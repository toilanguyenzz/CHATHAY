"""Zalo OA webhook server focused on text/file/image summarization."""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import config
from services.ai_summarizer import summarize_image, summarize_text
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

user_daily_usage: dict[str, dict] = {}
latest_summary_by_user: dict[str, dict[str, str]] = {}


def check_rate_limit(user_id: str) -> bool:
    today = time.strftime("%Y-%m-%d")
    if user_id not in user_daily_usage:
        user_daily_usage[user_id] = {"date": today, "count": 0}
    if user_daily_usage[user_id]["date"] != today:
        user_daily_usage[user_id] = {"date": today, "count": 0}
    return user_daily_usage[user_id]["count"] < config.FREE_DAILY_LIMIT


def increment_usage(user_id: str):
    today = time.strftime("%Y-%m-%d")
    if user_id not in user_daily_usage or user_daily_usage[user_id]["date"] != today:
        user_daily_usage[user_id] = {"date": today, "count": 0}
    user_daily_usage[user_id]["count"] += 1


def build_brief_summary(summary: str, max_len: int = 220) -> str:
    """Create a short, readable preview line from a full summary."""
    cleaned = " ".join(summary.replace("\n", " ").split())
    cleaned = cleaned.lstrip("-•*0123456789. )(").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def remember_summary(user_id: str, title: str, summary: str):
    latest_summary_by_user[user_id] = {
        "title": title,
        "summary": summary,
    }


def get_latest_summary(user_id: str) -> dict[str, str] | None:
    return latest_summary_by_user.get(user_id)


def verify_zalo_signature(request_body: bytes, mac_header: str) -> bool:
    """Verify the webhook MAC if a secret is configured."""
    if not ZALO_OA_SECRET or not mac_header:
        return True

    expected = hmac.new(
        ZALO_OA_SECRET.encode("utf-8"),
        request_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, mac_header)


async def send_text_message(user_id: str, text: str):
    """Send a plain text message to a Zalo OA user."""
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


def split_message_for_zalo(text: str, limit: int = ZALO_TEXT_LIMIT) -> list[str]:
    """Split a long message into Zalo-safe chunks."""
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


async def send_long_text_message(user_id: str, text: str):
    """Send one or more text messages while respecting Zalo's body size limit."""
    for chunk in split_message_for_zalo(text):
        await send_text_message(user_id, chunk)


async def download_zalo_file(file_url: str, save_path: str) -> bool:
    """Download a file from the direct URL provided by Zalo's webhook."""
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
    logger.info("Verification code: %s...", ZALO_VERIFICATION_CODE[:10])
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


async def process_webhook_event(body: dict):
    """Process a Zalo webhook event in the background."""
    try:
        event_name = body.get("event_name", "")
        sender_id = body.get("sender", {}).get("id", "")
        logger.info("Processing event: %s from %s", event_name, sender_id)

        if event_name == "follow":
            await send_text_message(
                sender_id,
                "Xin chao! Toi la tro ly AI tom tat tai lieu.\n\n"
                "Gui cho toi file PDF, Word, anh chup tai lieu, hoac mot doan text dai de bat dau.",
            )
            return

        if event_name == "user_send_text":
            text = body.get("message", {}).get("text", "")
            await handle_zalo_text(sender_id, text)
            return

        if event_name == "user_send_image":
            attachments = body.get("message", {}).get("attachments", [])
            if attachments:
                image_url = attachments[0].get("payload", {}).get("url", "")
                await handle_zalo_image(sender_id, image_url)
            return

        if event_name == "user_send_file":
            attachments = body.get("message", {}).get("attachments", [])
            if attachments:
                payload = attachments[0].get("payload", {})
                file_url = payload.get("url", "")
                file_name = payload.get("name", "document")
                file_size = payload.get("size", 0)
                await handle_zalo_file(sender_id, file_url, file_name, file_size)
            return

        logger.info("Unhandled event: %s", event_name)
    except Exception as exc:
        logger.error("Error processing event: %s", exc, exc_info=True)


async def send_audio_for_latest_summary(user_id: str):
    """Generate audio on demand for the user's latest summary."""
    latest = get_latest_summary(user_id)
    if not latest:
        await send_text_message(user_id, "Chua co ban tom tat nao gan day de doc. Gui tai lieu truoc nhe!")
        return

    if not config.FPT_AI_API_KEY:
        await send_text_message(user_id, "Tinh nang doc audio chua duoc bat tren he thong nay.")
        return

    await send_text_message(user_id, "Dang tao ban doc audio... Vui long doi them chut.")
    audio_path = await text_to_speech(latest["summary"])
    if not audio_path:
        await send_text_message(user_id, "Khong tao duoc audio luc nay. Ban thu lai sau nhe!")
        return

    audio_filename = os.path.basename(audio_path)
    audio_url = f"https://chathay-production.up.railway.app/audio/{audio_filename}"
    await send_text_message(
        user_id,
        f"Ban doc audio cho: {latest['title']}\nNghe tai day: {audio_url}",
    )
    asyncio.create_task(_cleanup_audio_later(audio_path))


async def _cleanup_audio_later(audio_path: str, delay_seconds: int = 3600):
    await asyncio.sleep(delay_seconds)
    await cleanup_audio(audio_path)


@app.post("/webhook/zalo")
async def zalo_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive and acknowledge Zalo webhook calls."""
    try:
        raw_body = await request.body()
        mac_header = request.headers.get("mac", "")
        if ZALO_OA_SECRET and mac_header and not verify_zalo_signature(raw_body, mac_header):
            raise HTTPException(status_code=403, detail="Invalid signature")

        body = json.loads(raw_body)
        event_name = body.get("event_name", "")
        sender_id = body.get("sender", {}).get("id", "unknown")
        logger.info("Webhook received: %s from %s", event_name, sender_id)

        background_tasks.add_task(process_webhook_event, body)
        return JSONResponse(content={"status": "ok"}, status_code=200)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Webhook error: %s", exc, exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=200)


async def handle_zalo_text(user_id: str, text: str):
    """Summarize long user text directly."""
    normalized_text = text.strip().lower()
    if normalized_text in {"nghe", "audio", "doc", "voice"}:
        await send_audio_for_latest_summary(user_id)
        return

    if len(text) < 10:
        await send_text_message(
            user_id,
            "Gui cho toi file PDF, Word, hoac anh chup tai lieu.\n"
            "Toi se tom tat thanh 5 y chinh cho ban.",
        )
        return

    if len(text) <= 100:
        await send_text_message(user_id, "Gui file hoac anh tai lieu cho toi de duoc tom tat!")
        return

    if not check_rate_limit(user_id):
        await send_text_message(
            user_id,
            f"Ban da dung het {config.FREE_DAILY_LIMIT} luot mien phi hom nay. Quay lai ngay mai nhe!",
        )
        return

    await send_text_message(user_id, "Dang tom tat van ban... Vui long doi.")
    summary = await summarize_text(text)
    brief = build_brief_summary(summary)
    remember_summary(user_id, "van ban ban vua gui", summary)
    await send_long_text_message(
        user_id,
        f"Tom tat nhanh: {brief}\n\nTom tat chi tiet:\n{summary}\n\nNeu can nghe ban doc, hay nhan: NGHE",
    )
    increment_usage(user_id)


async def handle_zalo_file(user_id: str, file_url: str, file_name: str, file_size):
    """Download, parse, and summarize a user file."""
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
        await send_text_message(
            user_id,
            "Toi chi ho tro file PDF, Word (.docx), hoac anh. Vui long gui dung dinh dang!",
        )
        return

    await send_text_message(user_id, "Dang xu ly tai lieu cua ban... Vui long doi khoang 15-30 giay.")
    start_time = time.time()
    file_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_{file_name}")

    try:
        if not await download_zalo_file(file_url, file_path):
            await send_text_message(user_id, "Khong the tai file. Vui long gui lai!")
            return

        text, _ftype = await extract_text(file_path, config.MAX_PAGES)
        if not text:
            await send_text_message(
                user_id,
                "Khong the doc duoc noi dung file nay. Thu chup anh tai lieu va gui anh cho toi!",
            )
            return

        summary = await summarize_text(text)
        elapsed = time.time() - start_time
        brief = build_brief_summary(summary)
        remember_summary(user_id, file_name, summary)
        await send_long_text_message(
            user_id,
            f"Tom tat tai lieu: {file_name}\n"
            f"Xu ly trong {elapsed:.0f} giay\n"
            f"Tom tat nhanh: {brief}\n\n"
            f"Tom tat chi tiet:\n{summary}\n\n"
            f"Neu can nghe ban doc, hay nhan: NGHE",
        )
        increment_usage(user_id)

    except Exception as exc:
        logger.error("File processing error: %s", exc, exc_info=True)
        await send_text_message(user_id, "Da xay ra loi. Vui long thu lai!")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def handle_zalo_image(user_id: str, image_url: str):
    """Download and summarize an image."""
    if not check_rate_limit(user_id):
        await send_text_message(user_id, f"Ban da dung het {config.FREE_DAILY_LIMIT} luot mien phi hom nay.")
        return

    await send_text_message(user_id, "Dang doc noi dung anh... Vui long doi khoang 15-30 giay.")
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

        summary = await summarize_image(image_path)
        elapsed = time.time() - start_time
        brief = build_brief_summary(summary)
        remember_summary(user_id, "anh ban vua gui", summary)
        await send_long_text_message(
            user_id,
            f"Tom tat tu anh chup:\n"
            f"Xu ly trong {elapsed:.0f} giay\n"
            f"Tom tat nhanh: {brief}\n\n"
            f"Tom tat chi tiet:\n{summary}\n\n"
            f"Neu can nghe ban doc, hay nhan: NGHE",
        )
        increment_usage(user_id)

    except Exception as exc:
        logger.error("Image processing error: %s", exc, exc_info=True)
        await send_text_message(user_id, "Khong doc duoc anh. Chup ro hon va thu lai!")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


if __name__ == "__main__":
    if not ZALO_OA_ACCESS_TOKEN:
        print("=" * 50)
        print("[WARN] ZALO_OA_ACCESS_TOKEN not set!")
        print("Bot will start but cannot send messages.")
        print("Add ZALO_OA_ACCESS_TOKEN to .env when ready.")
        print("=" * 50)

    print("=" * 50)
    print("[BOT] Zalo Doc Bot - Webhook Server")
    print("=" * 50)
    print(f"[*] Port: {config.PORT}")
    print("[*] Webhook URL: POST /webhook/zalo")
    print("[*] Health check: GET /")
    print("=" * 50)

    uvicorn.run(
        "zalo_webhook:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )
