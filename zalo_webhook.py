"""
Zalo OA Webhook Server — FastAPI
Khi Zalo OA được duyệt, chạy file này thay vì bot.py

Cách hoạt động:
1. User gửi file/ảnh qua Zalo OA
2. Zalo gọi webhook URL của bạn
3. Server xử lý file → AI tóm tắt → TTS → gửi lại qua Zalo OA API
"""

import os
import io
import json
import logging
import time
import uuid
import hashlib
import hmac
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException

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

# Zalo OA config — add these to your .env when ready
ZALO_OA_ACCESS_TOKEN = os.getenv("ZALO_OA_ACCESS_TOKEN", "")
ZALO_OA_SECRET = os.getenv("ZALO_OA_SECRET", "")
ZALO_API_URL = "https://openapi.zalo.me/v3.0/oa"

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


# ===== WEBHOOK HANDLER =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup/shutdown."""
    logger.info("Zalo OA Webhook Server starting...")
    logger.info(f"OA Token set: {'YES' if ZALO_OA_ACCESS_TOKEN else 'NO'}")
    yield
    logger.info("Server shutting down...")


app = FastAPI(
    title="Zalo Doc Bot — Webhook Server",
    lifespan=lifespan,
)


@app.get("/")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "zalo-doc-bot", "version": "1.0"}


@app.post("/webhook/zalo")
async def zalo_webhook(request: Request):
    """
    Handle incoming events from Zalo OA.
    
    Zalo sends events for:
    - user_send_text: User sends text message
    - user_send_image: User sends image
    - user_send_file: User sends file (PDF, docx, etc.)
    - follow/unfollow: User follows/unfollows OA
    """
    try:
        body = await request.json()
        event_name = body.get("event_name", "")
        sender_id = body.get("sender", {}).get("id", "")

        logger.info(f"Webhook event: {event_name} from {sender_id}")

        if event_name == "follow":
            # New follower — send welcome
            await send_text_message(sender_id, (
                "Xin chao! Toi la Tro ly AI Tai lieu.\n\n"
                "Gui cho toi bat ky file nao:\n"
                "- PDF, Word (.docx)\n"
                "- Anh chup tai lieu\n\n"
                "Toi se tom tat thanh 5 y chinh va doc to bang giong noi tieng Viet!\n\n"
                f"Mien phi {config.FREE_DAILY_LIMIT} tai lieu/ngay."
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

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


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


async def handle_zalo_file(user_id: str, token: str, file_name: str, file_size: int):
    """Handle file attachments from Zalo."""
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
