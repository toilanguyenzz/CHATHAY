"""Zalo OA webhook server with interactive summary flow."""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import config
from services.ai_summarizer import summarize_image_structured, summarize_text_structured
from services.document_parser import extract_text, get_file_type
from services.tts_service import cleanup_audio, text_to_speech

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ZALO_OA_ACCESS_TOKEN = os.getenv("ZALO_OA_ACCESS_TOKEN", "")
ZALO_OA_SECRET = os.getenv("ZALO_OA_SECRET", "")
ZALO_APP_ID = os.getenv("ZALO_APP_ID", "1534343952928885811")
ZALO_API_URL = "https://openapi.zalo.me/v3.0/oa"
ZALO_VERIFICATION_CODE = os.getenv(
    "ZALO_VERIFICATION_CODE",
    "VyM34AN4DmzorQGojDui9ZNWYXdPbbz5DZ0t",
)
ZALO_TEXT_LIMIT = 2900

user_daily_usage: dict[str, dict[str, int | str]] = {}
latest_summary_by_user: dict[str, dict[str, Any]] = {}


def check_rate_limit(user_id: str) -> bool:
    today = time.strftime("%Y-%m-%d")
    if user_id not in user_daily_usage:
        user_daily_usage[user_id] = {"date": today, "count": 0}
    if user_daily_usage[user_id]["date"] != today:
        user_daily_usage[user_id] = {"date": today, "count": 0}
    return int(user_daily_usage[user_id]["count"]) < config.FREE_DAILY_LIMIT


def increment_usage(user_id: str):
    today = time.strftime("%Y-%m-%d")
    if user_id not in user_daily_usage or user_daily_usage[user_id]["date"] != today:
        user_daily_usage[user_id] = {"date": today, "count": 0}
    user_daily_usage[user_id]["count"] = int(user_daily_usage[user_id]["count"]) + 1


def clean_preview_text(text: str, max_len: int = 180) -> str:
    cleaned = " ".join(text.replace("\n", " ").split()).strip()
    cleaned = cleaned.lstrip("-*0123456789. )(").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def remember_summary(user_id: str, title: str, structured_summary: dict[str, Any]):
    latest_summary_by_user[user_id] = {"title": title, "data": structured_summary}


def get_latest_summary(user_id: str) -> dict[str, Any] | None:
    return latest_summary_by_user.get(user_id)


def get_point_from_command(text: str) -> int | None:
    normalized = text.strip().lower()
    for token in normalized.replace("nghe", " ").replace("chi tiet", " ").split():
        if token.isdigit():
            value = int(token)
            if 1 <= value <= 5:
                return value
    if normalized.isdigit():
        value = int(normalized)
        if 1 <= value <= 5:
            return value
    return None


def split_message_for_zalo(text: str, limit: int = ZALO_TEXT_LIMIT) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if len(normalized) <= limit:
        return [normalized]

    chunks: list[str] = []
    remaining = normalized
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        split_at = remaining.rfind("\n\n", 0, limit)
        if split_at <= 0:
            split_at = remaining.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at <= 0:
            split_at = limit

        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].strip()

    return chunks


def format_summary_menu(title: str, structured_summary: dict[str, Any], elapsed_seconds: float | None = None) -> str:
    lines: list[str] = []
    lines.append(f"Đọc xong rồi! Đây là bản tóm tắt tài liệu '{title}' của bạn:")
    if elapsed_seconds is not None:
        lines.append(f"(Xử lý trong {elapsed_seconds:.0f} giây)")
    lines.append("")

    overview = structured_summary.get("overview", "")
    if overview:
        lines.append(f"📌 Tổng quan: {overview}\n")

    lines.append("5 ý chính:")
    for point in structured_summary.get("points", [])[:5]:
        lines.append(f"🔹 {point['index']}. {point['title']}: {clean_preview_text(point['brief'])}")

    lines.append("")
    lines.append("Bấm số 1–5 để nghe giải thích chi tiết từng ý.\nHoặc gõ câu hỏi bất kỳ về tài liệu này.")
    return "\n".join(lines)


def format_point_detail(structured_summary: dict[str, Any], point_index: int) -> str:
    point = structured_summary["points"][point_index - 1]
    return (
        f"📝 Ý {point_index}: {point['title']}\n\n"
        f"Chi tiết:\n{point['detail']}\n\n"
        f"🎧 Để nghe đọc ý này, hãy nhắn: NGHE {point_index}"
    )


def verify_zalo_signature(request_body: bytes, mac_header: str) -> bool:
    if not ZALO_OA_SECRET or not mac_header:
        return True
    expected = hmac.new(
        ZALO_OA_SECRET.encode("utf-8"),
        request_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, mac_header)


async def send_text_message(user_id: str, text: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{ZALO_API_URL}/message/cs",
            headers={
                "Content-Type": "application/json",
                "access_token": ZALO_OA_ACCESS_TOKEN,
            },
            json={
                "recipient": {"user_id": user_id},
                "message": {"text": text},
            },
        )

    result = response.json()
    if result.get("error") != 0:
        logger.error("Zalo send failed: %s", result)
    return result


async def send_long_text_message(user_id: str, text: str):
    for chunk in split_message_for_zalo(text):
        await send_text_message(user_id, chunk)


async def download_zalo_file(file_url: str, save_path: str) -> bool:
    if not file_url:
        logger.error("No file URL provided")
        return False

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        try:
            logger.info("Downloading file from: %s...", file_url[:80])
            response = await client.get(file_url)
            if response.status_code != 200:
                logger.error("Download failed with status: %s", response.status_code)
                return False
            with open(save_path, "wb") as output_file:
                output_file.write(response.content)
            logger.info("File downloaded: %s bytes", len(response.content))
            return True
        except Exception as exc:
            logger.error("Download error: %s", exc)
            return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Zalo OA Webhook Server starting...")
    logger.info("OA Token set: %s", "YES" if ZALO_OA_ACCESS_TOKEN else "NO")
    logger.info("OA Secret set: %s", "YES" if ZALO_OA_SECRET else "NO")
    logger.info("App ID: %s", ZALO_APP_ID)
    logger.info("=" * 60)
    yield
    logger.info("Server shutting down...")


app = FastAPI(title="Zalo Doc Bot Webhook Server", lifespan=lifespan)
app.mount("/audio", StaticFiles(directory=config.AUDIO_DIR), name="audio")

HOMEPAGE_HTML = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta name="zalo-platform-site-verification" content="{ZALO_VERIFICATION_CODE}" />
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zalo Doc Bot</title>
</head>
<body>
<h1>Zalo Doc Bot</h1>
<p>Server is running.</p>
<p>App ID: {ZALO_APP_ID}</p>
<p>Webhook: POST /webhook/zalo</p>
</body>
</html>"""

VERIFIER_HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta name="zalo-platform-site-verification" content="{ZALO_VERIFICATION_CODE}" />
</head>
<body>{ZALO_VERIFICATION_CODE}</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def health():
    return HTMLResponse(content=HOMEPAGE_HTML, status_code=200)


@app.get(f"/zalo_verifier{ZALO_VERIFICATION_CODE}.html", response_class=HTMLResponse)
async def zalo_verifier():
    return HTMLResponse(content=VERIFIER_HTML, status_code=200)


@app.get("/webhook/zalo")
async def webhook_verify():
    return JSONResponse(content={"status": "ok", "message": "Zalo webhook is active"}, status_code=200)


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """Web Upload Portal — Kéo thả file, nhận tóm tắt AI ngay trên trình duyệt."""
    html_path = os.path.join(os.path.dirname(__file__), "static", "upload.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.post("/api/summarize")
async def api_summarize(file: UploadFile = File(...)):
    """API endpoint cho Web Upload Portal. Nhận file, trả JSON tóm tắt."""
    try:
        file_name = file.filename or "document"
        file_type = get_file_type(file_name)

        if file_type == "unknown":
            return JSONResponse(content={"error": "Chỉ hỗ trợ PDF, Word (.docx), hoặc ảnh."}, status_code=400)

        # Save temp file
        file_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_{file_name}")
        content = await file.read()

        if len(content) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            return JSONResponse(content={"error": f"File quá lớn! Tối đa {config.MAX_FILE_SIZE_MB}MB."}, status_code=400)

        with open(file_path, "wb") as f:
            f.write(content)

        try:
            if file_type == "image":
                structured = await summarize_image_structured(file_path)
            else:
                text, _ft = await extract_text(file_path, config.MAX_PAGES)
                if not text:
                    return JSONResponse(content={"error": "Không đọc được nội dung file này."}, status_code=400)
                structured = await summarize_text_structured(text)

            if structured.get("error"):
                return JSONResponse(content={"error": str(structured["error"])}, status_code=500)

            return JSONResponse(content=structured, status_code=200)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as exc:
        logger.error("API summarize error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": "Đã xảy ra lỗi. Vui lòng thử lại!"}, status_code=500)


@app.post("/api/summarize-view", response_class=HTMLResponse)
async def api_summarize_view(file: UploadFile = File(...)):
    """Upload file → trả về trang HTML kết quả đẹp (cho Send To trên Windows)."""
    try:
        file_name = file.filename or "document"
        file_type = get_file_type(file_name)

        if file_type == "unknown":
            return HTMLResponse(content="<h1>Chỉ hỗ trợ PDF, Word, hoặc ảnh.</h1>", status_code=400)

        file_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_{file_name}")
        content = await file.read()

        if len(content) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            return HTMLResponse(content=f"<h1>File quá lớn! Tối đa {config.MAX_FILE_SIZE_MB}MB.</h1>", status_code=400)

        with open(file_path, "wb") as f:
            f.write(content)

        try:
            if file_type == "image":
                structured = await summarize_image_structured(file_path)
            else:
                text, _ft = await extract_text(file_path, config.MAX_PAGES)
                if not text:
                    return HTMLResponse(content="<h1>Không đọc được nội dung file này.</h1>", status_code=400)
                structured = await summarize_text_structured(text)

            if structured.get("error"):
                return HTMLResponse(content=f"<h1>{structured['error']}</h1>", status_code=500)

            # Build beautiful HTML result page
            title = structured.get("document_title", "Tài liệu")
            overview = structured.get("overview", "")
            points_html = ""
            for p in structured.get("points", []):
                points_html += f"""<div class="c" onclick="this.classList.toggle('o')">
                    <div class="h"><div class="n">{p['index']}</div><div class="tt">{p['title']}</div><div class="tg">▼</div></div>
                    <div class="b">{p['brief']}</div>
                    <div class="d">{p['detail']}</div></div>"""

            html = f"""<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Read AI — {title}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Inter',sans-serif;background:#0a0e1a;color:#f0f0f5;padding:40px 20px}}
body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 20% 50%,rgba(108,92,231,.12) 0%,transparent 50%),radial-gradient(ellipse at 80% 20%,rgba(0,206,201,.08) 0%,transparent 50%);pointer-events:none}}
.w{{max-width:700px;margin:0 auto;position:relative;z-index:1}}.logo{{text-align:center;font-size:32px;font-weight:800;background:linear-gradient(135deg,#6c5ce7,#00cec9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px}}
.sub{{text-align:center;color:#8892b0;font-size:13px;margin-bottom:28px}}.hdr{{background:linear-gradient(135deg,#131829,#1a2035);border:1px solid #2d3555;border-radius:16px;padding:24px;margin-bottom:16px}}
.dt{{font-size:20px;font-weight:700;margin-bottom:8px}}.ov{{color:#8892b0;font-size:14px;line-height:1.6;padding-left:12px;border-left:3px solid #6c5ce7}}
.c{{background:#131829;border:1px solid #2d3555;border-radius:14px;margin-bottom:10px;cursor:pointer;overflow:hidden;transition:all .3s}}.c:hover{{border-color:#6c5ce7;transform:translateX(4px)}}
.h{{display:flex;align-items:center;gap:12px;padding:16px 20px}}.n{{width:32px;height:32px;background:linear-gradient(135deg,#6c5ce7,#a29bfe);border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0}}
.tt{{font-weight:600;font-size:15px;flex:1}}.tg{{color:#8892b0;transition:transform .3s;font-size:16px}}.c.o .tg{{transform:rotate(180deg)}}
.b{{padding:0 20px 12px;font-size:13px;color:#8892b0}}.d{{display:none;padding:16px 20px;font-size:14px;line-height:1.7;border-top:1px solid #2d3555}}
.c.o .d{{display:block}}.fb{{text-align:center;color:#8892b0;font-size:12px;margin-top:20px}}</style></head>
<body><div class="w"><div class="logo">📖 Read AI</div><div class="sub">Kết quả tóm tắt tài liệu</div>
<div class="hdr"><div class="dt">📖 {title}</div><div class="ov">{overview}</div></div>
{points_html}<div class="fb">📄 File: {file_name}</div></div></body></html>"""
            return HTMLResponse(content=html, status_code=200)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as exc:
        logger.error("API summarize-view error: %s", exc, exc_info=True)
        return HTMLResponse(content="<h1>Đã xảy ra lỗi. Vui lòng thử lại!</h1>", status_code=500)


async def send_audio_for_point(user_id: str, point_index: int):
    latest = get_latest_summary(user_id)
    if not latest:
        await send_text_message(user_id, "Chua co ban tom tat nao gan day. Gui tai lieu truoc nhe!")
        return
    if not config.FPT_AI_API_KEY:
        await send_text_message(user_id, "Tinh nang doc audio chua duoc bat tren he thong nay.")
        return

    points = latest["data"]["points"]
    if not 1 <= point_index <= len(points):
        await send_text_message(user_id, "Chi so khong hop le. Hay chon tu 1 den 5.")
        return

    point = points[point_index - 1]
    await send_text_message(user_id, f"Dang tao audio cho y {point_index}: {point['title']}")
    audio_path = await text_to_speech(point["detail"])
    if not audio_path:
        await send_text_message(user_id, "Khong tao duoc audio luc nay. Ban thu lai sau nhe!")
        return

    audio_filename = os.path.basename(audio_path)
    audio_url = f"https://chathay-production.up.railway.app/audio/{audio_filename}"
    await send_text_message(user_id, f"Nghe y {point_index} tai day:\n{audio_url}")
    asyncio.create_task(_cleanup_audio_later(audio_path))


async def _cleanup_audio_later(audio_path: str, delay_seconds: int = 3600):
    await asyncio.sleep(delay_seconds)
    await cleanup_audio(audio_path)


async def handle_interactive_command(user_id: str, text: str) -> bool:
    normalized = text.strip().lower()
    latest = get_latest_summary(user_id)

    if normalized.startswith("nghe"):
        point_index = get_point_from_command(normalized)
        if point_index is None:
            await send_text_message(user_id, "Hay nhan theo mau: NGHE 1, NGHE 2, ..., NGHE 5")
            return True
        await send_audio_for_point(user_id, point_index)
        return True

    if latest and normalized.isdigit():
        point_index = int(normalized)
        if 1 <= point_index <= 5:
            await send_long_text_message(user_id, format_point_detail(latest["data"], point_index))
            return True

    if latest and normalized.startswith("chi tiet"):
        point_index = get_point_from_command(normalized)
        if point_index is not None:
            await send_long_text_message(user_id, format_point_detail(latest["data"], point_index))
            return True

    return False


async def process_webhook_event(body: dict):
    try:
        event_name = body.get("event_name", "")
        sender_id = body.get("sender", {}).get("id", "")
        logger.info("Processing event: %s from %s", event_name, sender_id)

        if event_name == "follow":
            await send_text_message(
                sender_id,
                "Xin chao! Toi la tro ly AI tom tat tai lieu.\nGui cho toi file PDF, Word, anh chup tai lieu hoac mot doan text dai de bat dau.",
            )
            return

        if event_name == "user_send_text":
            await handle_zalo_text(sender_id, body.get("message", {}).get("text", ""))
            return

        if event_name == "user_send_image":
            attachments = body.get("message", {}).get("attachments", [])
            if attachments:
                await handle_zalo_image(sender_id, attachments[0].get("payload", {}).get("url", ""))
            return

        if event_name == "user_send_file":
            attachments = body.get("message", {}).get("attachments", [])
            if attachments:
                payload = attachments[0].get("payload", {})
                await handle_zalo_file(
                    sender_id,
                    payload.get("url", ""),
                    payload.get("name", "document"),
                    payload.get("size", 0),
                )
            return

        logger.info("Unhandled event: %s", event_name)
    except Exception as exc:
        logger.error("Error processing event: %s", exc, exc_info=True)


@app.post("/webhook/zalo")
async def zalo_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        raw_body = await request.body()
        mac_header = request.headers.get("mac", "")
        if ZALO_OA_SECRET and mac_header and not verify_zalo_signature(raw_body, mac_header):
            raise HTTPException(status_code=403, detail="Invalid signature")

        body = json.loads(raw_body)
        logger.info("Webhook received: %s from %s", body.get("event_name", ""), body.get("sender", {}).get("id", "unknown"))
        background_tasks.add_task(process_webhook_event, body)
        return JSONResponse(content={"status": "ok"}, status_code=200)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Webhook error: %s", exc, exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=200)


async def handle_zalo_text(user_id: str, text: str):
    normalized = text.strip().lower()
    if await handle_interactive_command(user_id, normalized):
        return

    if len(text.strip()) < 10:
        await send_text_message(
            user_id,
            "Gui cho toi file PDF, Word, hoac anh chup tai lieu.\nToi se tach ra 5 y chinh de ban chon xem ky tung y.",
        )
        return

    if len(text.strip()) <= 100:
        await send_text_message(user_id, "Gui file hoac anh tai lieu, hoac mot doan text dai hon de toi tom tat.")
        return

    if not check_rate_limit(user_id):
        await send_text_message(user_id, f"Ban da dung het {config.FREE_DAILY_LIMIT} luot mien phi hom nay. Quay lai ngay mai nhe!")
        return

    await send_text_message(user_id, "Bot đang đọc tài liệu của bạn... Vui lòng chờ 15–30 giây nhé.")
    structured = await summarize_text_structured(text)
    if structured.get("error"):
        await send_text_message(user_id, str(structured["error"]))
        return

    remember_summary(user_id, "van ban ban vua gui", structured)
    await send_long_text_message(user_id, format_summary_menu("van ban ban vua gui", structured))
    increment_usage(user_id)


async def handle_zalo_file(user_id: str, file_url: str, file_name: str, file_size):
    try:
        file_size = int(file_size)
    except (ValueError, TypeError):
        file_size = 0

    if not check_rate_limit(user_id):
        await send_text_message(user_id, f"Ban da dung het {config.FREE_DAILY_LIMIT} luot mien phi hom nay.")
        return

    if file_size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
        await send_text_message(user_id, f"File qua lon! Toi da {config.MAX_FILE_SIZE_MB}MB.")
        return

    if get_file_type(file_name) == "unknown":
        await send_text_message(user_id, "Toi chi ho tro file PDF, Word (.docx), hoac anh. Vui long gui dung dinh dang!")
        return

    await send_text_message(user_id, "Bot đang đọc tài liệu của bạn... Vui lòng chờ 15–30 giây nhé.")
    start_time = time.time()
    file_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_{file_name}")

    try:
        if not await download_zalo_file(file_url, file_path):
            await send_text_message(user_id, "Khong the tai file. Vui long gui lai!")
            return

        text, _file_type = await extract_text(file_path, config.MAX_PAGES)
        if not text:
            await send_text_message(user_id, "Khong the doc duoc noi dung file nay. Thu chup anh tai lieu va gui anh cho toi!")
            return

        structured = await summarize_text_structured(text)
        if structured.get("error"):
            await send_text_message(user_id, str(structured["error"]))
            return

        remember_summary(user_id, file_name, structured)
        await send_long_text_message(user_id, format_summary_menu(file_name, structured, time.time() - start_time))
        increment_usage(user_id)
    except Exception as exc:
        logger.error("File processing error: %s", exc, exc_info=True)
        await send_text_message(user_id, "Da xay ra loi. Vui long thu lai!")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def handle_zalo_image(user_id: str, image_url: str):
    if not check_rate_limit(user_id):
        await send_text_message(user_id, f"Ban da dung het {config.FREE_DAILY_LIMIT} luot mien phi hom nay.")
        return

    await send_text_message(user_id, "Bot đang đọc ảnh của bạn... Vui lòng chờ 15–30 giây nhé.")
    start_time = time.time()
    image_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}.jpg")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                await send_text_message(user_id, "Khong tai duoc anh. Gui lai nhe!")
                return
            with open(image_path, "wb") as image_file:
                image_file.write(response.content)

        structured = await summarize_image_structured(image_path)
        if structured.get("error"):
            await send_text_message(user_id, str(structured["error"]))
            return

        remember_summary(user_id, "anh ban vua gui", structured)
        await send_long_text_message(user_id, format_summary_menu("anh ban vua gui", structured, time.time() - start_time))
        increment_usage(user_id)
    except Exception as exc:
        logger.error("Image processing error: %s", exc, exc_info=True)
        await send_text_message(user_id, "Khong doc duoc anh. Chup ro hon va thu lai!")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


if __name__ == "__main__":
    uvicorn.run(
        "zalo_webhook:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )
