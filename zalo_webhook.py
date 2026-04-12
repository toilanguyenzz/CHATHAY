"""
Zalo OA Webhook Server — FastAPI
Khi Zalo OA được duyệt, chạy file này thay vì bot.py

Cách hoạt động:
1. User gửi file/ảnh qua Zalo OA
2. Zalo gọi webhook URL của bạn
3. Server xử lý file → AI tóm tắt → TTS → gửi lại qua Zalo OA API

Xác thực domain:
- Meta tag trên trang chủ (GET /)
- File xác thực tại /verifierXXXX.html
- Webhook URL phải trả 200 OK cho GET request
"""

import os
import io
import json
import logging
import time
import uuid
import hashlib
import hmac
import asyncio
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse

from config import config
from services.document_parser import extract_text, get_file_type
from services.ai_summarizer import summarize_text, summarize_image
from services.tts_service import text_to_speech, cleanup_audio

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Zalo OA config
ZALO_OA_ACCESS_TOKEN = os.getenv("ZALO_OA_ACCESS_TOKEN", "")
ZALO_OA_SECRET = os.getenv("ZALO_OA_SECRET", "")
ZALO_APP_ID = os.getenv("ZALO_APP_ID", "1534343952928885811")
ZALO_API_URL = "https://openapi.zalo.me/v3.0/oa"

# ===== DOMAIN VERIFICATION CONFIG =====
# Lấy mã này từ trang Zalo Developers > Xác thực domain
# Khi bấm "Xác thực", Zalo sẽ hiện mã meta tag, copy content vào đây
ZALO_VERIFICATION_CODE = os.getenv(
    "ZALO_VERIFICATION_CODE",
    "VyM34AN4DmzorQGojDui9ZNWYXdPbbz5DZOt"
)

# Rate limiting (in-memory, same as Telegram bot)
user_daily_usage: dict[str, dict] = {}


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


def verify_zalo_signature(request_body: bytes, mac_header: str) -> bool:
    """
    Xác thực chữ ký webhook từ Zalo.
    Tạm thời bypass để nhận mọi webhook trong lúc test.
    """
    return True


# ===== ZALO OA API HELPERS =====

async def send_text_message(user_id: str, text: str):
    """Send a text message to a Zalo user."""
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
            logger.error(f"Zalo send failed: {result}")
        return result


async def send_file_message(user_id: str, file_path: str, file_type: str = "voice"):
    """
    Send a file (audio/image/file) to a Zalo user.
    For voice messages, Zalo requires uploading first.
    """
    # Step 1: Upload file to Zalo
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(file_path, "rb") as f:
            upload_response = await client.post(
                f"{ZALO_API_URL}/upload/file",
                headers={"access_token": ZALO_OA_ACCESS_TOKEN},
                files={"file": (os.path.basename(file_path), f, "audio/mpeg")},
            )

        upload_result = upload_response.json()
        if upload_result.get("error") != 0:
            logger.error(f"Zalo upload failed: {upload_result}")
            return None

        attachment_id = upload_result.get("data", {}).get("attachment_id")

        # Step 2: Send the uploaded file as message
        response = await client.post(
            f"{ZALO_API_URL}/message/cs",
            headers={
                "Content-Type": "application/json",
                "access_token": ZALO_OA_ACCESS_TOKEN,
            },
            json={
                "recipient": {"user_id": user_id},
                "message": {
                    "attachment": {
                        "type": "file",
                        "payload": {"token": attachment_id},
                    }
                },
            },
        )
        return response.json()


async def download_zalo_file(token: str, save_path: str) -> bool:
    """Download a file from Zalo using the attachment token."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get file URL from Zalo
        response = await client.get(
            f"{ZALO_API_URL}/getfile",
            headers={"access_token": ZALO_OA_ACCESS_TOKEN},
            params={"token": token},
        )
        result = response.json()

        if result.get("error") != 0:
            logger.error(f"Get file URL failed: {result}")
            return False

        file_url = result.get("data", {}).get("url")
        if not file_url:
            return False

        # Download the file
        file_response = await client.get(file_url)
        if file_response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(file_response.content)
            return True

    return False


# ===== APP SETUP =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup/shutdown."""
    logger.info("=" * 60)
    logger.info("Zalo OA Webhook Server starting...")
    logger.info(f"OA Token set: {'YES' if ZALO_OA_ACCESS_TOKEN else 'NO'}")
    logger.info(f"OA Secret set: {'YES' if ZALO_OA_SECRET else 'NO'}")
    logger.info(f"App ID: {ZALO_APP_ID}")
    logger.info(f"Verification code: {ZALO_VERIFICATION_CODE[:10]}...")
    logger.info("=" * 60)
    yield
    logger.info("Server shutting down...")


app = FastAPI(
    title="Zalo Doc Bot — Webhook Server",
    lifespan=lifespan,
)


# ===== DOMAIN VERIFICATION ENDPOINTS =====
# Zalo yêu cầu xác thực domain bằng 1 trong 2 cách:
# 1. Meta tag trong <head> trang chủ (phải ĐẦU TIÊN trong <head>)
# 2. File HTML tại root: /zalo_verifierXXXX.html

# HTML cho trang chủ — meta tag verification PHẢI ở đầu <head>
HOMEPAGE_HTML = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta name="zalo-platform-site-verification" content="{ZALO_VERIFICATION_CODE}" />
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zalo Doc Bot</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f0f2f5; }}
.card {{ background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
h1 {{ color: #0068ff; margin-bottom: 10px; }}
.status {{ color: #00c851; font-weight: bold; }}
.info {{ color: #666; font-size: 14px; margin-top: 20px; }}
</style>
</head>
<body>
<div class="card">
<h1>Zalo Doc Bot</h1>
<p class="status">Server is running!</p>
<p>Tro ly AI tom tat tai lieu qua Zalo OA</p>
<div class="info">
<p>App ID: {ZALO_APP_ID}</p>
<p>Webhook: POST /webhook/zalo</p>
</div>
</div>
</body>
</html>"""

# HTML cho file verification — nội dung TỐI GIẢN, chỉ chứa verification code
VERIFIER_HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta name="zalo-platform-site-verification" content="{ZALO_VERIFICATION_CODE}" />
</head>
<body>{ZALO_VERIFICATION_CODE}</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def health():
    """
    Trang chủ — chứa meta tag xác thực domain.
    Meta tag 'zalo-platform-site-verification' đặt ĐẦU TIÊN trong <head>.
    """
    return HTMLResponse(content=HOMEPAGE_HTML, status_code=200)


@app.get(f"/zalo_verifier{ZALO_VERIFICATION_CODE}.html", response_class=HTMLResponse)
async def zalo_verifier_file_exact():
    """
    File xác thực domain — nội dung tối giản chỉ chứa verification code.
    URL: https://chathay-production.up.railway.app/zalo_verifierVyM34AN4DmzorQGojDui9ZNWYXdPbbz5DZ0t.html
    """
    return HTMLResponse(
        content=VERIFIER_HTML,
        status_code=200,
    )


# ===== WEBHOOK ENDPOINTS =====

@app.get("/webhook/zalo")
async def webhook_verify():
    """
    GET endpoint cho webhook — Zalo gửi GET request để verify URL.
    Phải trả về HTTP 200 OK.
    """
    return JSONResponse(
        content={"status": "ok", "message": "Zalo webhook is active"},
        status_code=200,
    )


async def process_webhook_event(body: dict):
    """Background task xử lý webhook event (để trả 200 nhanh cho Zalo)."""
    try:
        event_name = body.get("event_name", "")
        sender_id = body.get("sender", {}).get("id", "")

        logger.info(f"Processing event: {event_name} from {sender_id}")

        if event_name == "follow":
            # New follower — send welcome
            await send_text_message(sender_id, (
                "Xin chào! Tôi là Trợ lý AI Tài liệu 📄\n\n"
                "Gửi cho tôi bất kỳ file nào:\n"
                "• PDF, Word (.docx)\n"
                "• Ảnh chụp tài liệu\n\n"
                "Tôi sẽ tóm tắt thành 5 ý chính và đọc to bằng giọng nói tiếng Việt!\n\n"
                f"Miễn phí {config.FREE_DAILY_LIMIT} tài liệu/ngày."
            ))

        elif event_name == "user_send_text":
            text = body.get("message", {}).get("text", "")
            await handle_zalo_text(sender_id, text)

        elif event_name == "user_send_image":
            attachments = body.get("message", {}).get("attachments", [])
            if attachments:
                image_url = attachments[0].get("payload", {}).get("url", "")
                await handle_zalo_image(sender_id, image_url)

        elif event_name == "user_send_file":
            attachments = body.get("message", {}).get("attachments", [])
            if attachments:
                payload = attachments[0].get("payload", {})
                token = payload.get("token", "")
                file_name = payload.get("name", "document")
                file_size = payload.get("size", 0)
                await handle_zalo_file(sender_id, token, file_name, file_size)

        elif event_name == "unfollow":
            logger.info(f"User {sender_id} unfollowed OA")

        else:
            logger.info(f"Unhandled event: {event_name}")

    except Exception as e:
        logger.error(f"Error processing event: {e}", exc_info=True)


@app.post("/webhook/zalo")
async def zalo_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming events from Zalo OA.
    
    QUAN TRỌNG: Phải trả về 200 OK trong vòng 5 giây,
    nếu không Zalo sẽ retry và có thể disable webhook.
    → Dùng BackgroundTasks để xử lý async.
    
    Zalo sends events for:
    - user_send_text: User sends text message
    - user_send_image: User sends image
    - user_send_file: User sends file (PDF, docx, etc.)
    - follow/unfollow: User follows/unfollows OA
    """
    try:
        # Đọc raw body để verify signature
        raw_body = await request.body()

        # Verify webhook signature (nếu có OA Secret)
        mac_header = request.headers.get("mac", "")
        if ZALO_OA_SECRET and mac_header:
            if not verify_zalo_signature(raw_body, mac_header):
                logger.warning("Webhook signature verification FAILED!")
                raise HTTPException(status_code=403, detail="Invalid signature")

        body = json.loads(raw_body)
        event_name = body.get("event_name", "")
        sender_id = body.get("sender", {}).get("id", "unknown")

        logger.info(f"Webhook received: {event_name} from {sender_id}")

        # Xử lý trong background để trả 200 nhanh
        background_tasks.add_task(process_webhook_event, body)

        return JSONResponse(
            content={"status": "ok"},
            status_code=200,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        # Vẫn trả 200 để Zalo không retry
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=200,
        )


# ===== MESSAGE HANDLERS =====

async def handle_zalo_text(user_id: str, text: str):
    """Handle text messages from Zalo."""
    if len(text) < 10:
        await send_text_message(user_id, (
            "Gui cho toi file PDF, Word, hoac anh chup tai lieu.\n"
            "Toi se tom tat thanh 5 y chinh va doc to cho ban nghe!"
        ))
        return

    if len(text) > 100:
        if not check_rate_limit(user_id):
            await send_text_message(user_id,
                f"Ban da dung het {config.FREE_DAILY_LIMIT} luot mien phi hom nay. "
                "Quay lai ngay mai nhe!"
            )
            return

        await send_text_message(user_id, "Dang tom tat van ban... Vui long doi.")
        summary = await summarize_text(text)
        await send_text_message(user_id, f"Tom tat van ban:\n\n{summary}")
        increment_usage(user_id)

        # TTS
        if config.FPT_AI_API_KEY:
            clean = summary.replace("**", "").replace("*", "")
            audio_path = await text_to_speech(clean)
            if audio_path:
                await send_file_message(user_id, audio_path)
                await cleanup_audio(audio_path)
    else:
        await send_text_message(user_id,
            "Gui file hoac anh tai lieu cho toi de duoc tom tat!"
        )


async def handle_zalo_file(user_id: str, token: str, file_name: str, file_size):
    """Handle file attachments from Zalo."""
    # Zalo có thể gửi file_size dạng string, cần convert
    try:
        file_size = int(file_size)
    except (ValueError, TypeError):
        file_size = 0

    if not check_rate_limit(user_id):
        await send_text_message(user_id,
            f"Ban da dung het {config.FREE_DAILY_LIMIT} luot mien phi hom nay."
        )
        return

    if file_size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
        await send_text_message(user_id, f"File qua lon! Toi da {config.MAX_FILE_SIZE_MB}MB.")
        return

    file_type = get_file_type(file_name)
    if file_type == "unknown":
        await send_text_message(user_id,
            "Toi chi ho tro file PDF, Word (.docx), hoac anh. "
            "Vui long gui dung dinh dang!"
        )
        return

    await send_text_message(user_id,
        "Dang xu ly tai lieu cua ban... Vui long doi khoang 15-30 giay."
    )

    start_time = time.time()
    file_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_{file_name}")

    try:
        # Download file from Zalo
        success = await download_zalo_file(token, file_path)
        if not success:
            await send_text_message(user_id, "Khong the tai file. Vui long gui lai!")
            return

        # Extract text
        text, ftype = await extract_text(file_path, config.MAX_PAGES)

        if not text:
            await send_text_message(user_id,
                "Khong the doc duoc noi dung file nay. "
                "Thu chup anh tai lieu va gui anh cho toi!"
            )
            return

        # AI Summarize
        summary = await summarize_text(text)
        elapsed = time.time() - start_time

        await send_text_message(user_id,
            f"Tom tat tai lieu: {file_name}\n"
            f"Xu ly trong {elapsed:.0f} giay\n\n"
            f"{summary}"
        )

        # TTS
        if config.FPT_AI_API_KEY:
            clean = summary.replace("**", "").replace("*", "")
            audio_path = await text_to_speech(clean)
            if audio_path:
                await send_file_message(user_id, audio_path)
                await cleanup_audio(audio_path)

        increment_usage(user_id)

    except Exception as e:
        logger.error(f"File processing error: {e}", exc_info=True)
        await send_text_message(user_id, "Da xay ra loi. Vui long thu lai!")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def handle_zalo_image(user_id: str, image_url: str):
    """Handle image messages from Zalo."""
    if not check_rate_limit(user_id):
        await send_text_message(user_id,
            f"Ban da dung het {config.FREE_DAILY_LIMIT} luot mien phi hom nay."
        )
        return

    await send_text_message(user_id,
        "Dang doc noi dung anh... Vui long doi khoang 15-30 giay."
    )

    start_time = time.time()
    image_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}.jpg")

    try:
        # Download image from URL
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                await send_text_message(user_id, "Khong tai duoc anh. Gui lai nhe!")
                return
            with open(image_path, "wb") as f:
                f.write(response.content)

        # Summarize with Gemini vision
        summary = await summarize_image(image_path)
        elapsed = time.time() - start_time

        await send_text_message(user_id,
            f"Tom tat tu anh chup:\n"
            f"Xu ly trong {elapsed:.0f} giay\n\n"
            f"{summary}"
        )

        # TTS
        if config.FPT_AI_API_KEY:
            clean = summary.replace("**", "").replace("*", "")
            audio_path = await text_to_speech(clean)
            if audio_path:
                await send_file_message(user_id, audio_path)
                await cleanup_audio(audio_path)

        increment_usage(user_id)

    except Exception as e:
        logger.error(f"Image processing error: {e}", exc_info=True)
        await send_text_message(user_id, "Khong doc duoc anh. Chup ro hon va thu lai!")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


# ===== MAIN =====

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
    print(f"[*] Webhook URL: POST /webhook/zalo")
    print(f"[*] Health check: GET /")
    print("=" * 50)

    uvicorn.run(
        "zalo_webhook:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )
