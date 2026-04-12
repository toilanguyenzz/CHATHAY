"""FPT.AI Text-to-Speech service — Vietnamese voice synthesis.

FPT.AI TTS API v5 giới hạn ~500 ký tự/lần gọi.
Service này tự chia nhỏ text dài → gọi nhiều lần → ghép audio thành 1 file.
"""

import os
import logging
import httpx
import uuid
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from config import config

logger = logging.getLogger(__name__)

FPT_TTS_URL = "https://api.fpt.ai/hmi/tts/v5"
# FPT.AI giới hạn thực tế khoảng 500 ký tự/request
CHUNK_SIZE = 450


def split_text_smart(text: str, max_chars: int = CHUNK_SIZE) -> list[str]:
    """
    Chia text thành các đoạn nhỏ, cắt tại dấu chấm/dấu phẩy
    để giọng đọc tự nhiên, không bị ngắt giữa câu.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        # Tìm vị trí cắt tốt nhất (tại dấu chấm, dấu chấm hỏi, dấu chấm than)
        cut_at = -1
        for sep in ['. ', '.\n', '? ', '! ', ';\n', '; ', ',\n', ', ']:
            pos = remaining[:max_chars].rfind(sep)
            if pos > cut_at:
                cut_at = pos + len(sep)

        # Nếu không tìm thấy dấu câu, cắt tại khoảng trắng gần nhất
        if cut_at <= 0:
            cut_at = remaining[:max_chars].rfind(' ')

        # Nếu vẫn không có, cắt cứng
        if cut_at <= 0:
            cut_at = max_chars

        chunk = remaining[:cut_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut_at:].strip()

    return chunks


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _tts_single_chunk(client: httpx.AsyncClient, text: str, voice: str) -> bytes | None:
    """Gọi FPT.AI TTS cho 1 đoạn text ngắn, trả về bytes audio."""
    try:
        headers = {
            "api-key": config.FPT_AI_API_KEY,
            "speed": "0",
            "voice": voice,
        }

        response = await client.post(
            FPT_TTS_URL,
            headers=headers,
            data=text.encode("utf-8"),
        )

        if response.status_code != 200:
            logger.error(f"FPT.AI TTS failed: {response.status_code} {response.text}")
            return None

        result = response.json()
        audio_url = result.get("async")

        if not audio_url:
            logger.error(f"No audio URL in response: {result}")
            return None

        # Đợi FPT xử lý (thường 2-5 giây)
        for attempt in range(4):
            await asyncio.sleep(2 + attempt)
            audio_response = await client.get(audio_url)
            if audio_response.status_code == 200 and len(audio_response.content) > 100:
                return audio_response.content

        logger.error(f"Audio download failed after retries")
        return None

    except Exception as e:
        logger.error(f"TTS chunk error: {e}")
        return None


async def text_to_speech(text: str, voice: str = None) -> str | None:
    """
    Convert text to Vietnamese speech using FPT.AI TTS.
    Tự chia nhỏ text dài → gọi API nhiều lần → ghép audio.

    Args:
        text: Vietnamese text to convert
        voice: Voice name (banmai, leminh, thuminh, giahuy, myan, lannhi)

    Returns:
        Path to the generated .mp3 file, or None if failed
    """
    if not config.FPT_AI_API_KEY:
        logger.warning("FPT_AI_API_KEY not set, skipping TTS")
        return None

    voice = voice or config.FPT_AI_VOICE

    # Giới hạn tổng tối đa để tránh lạm dụng
    max_total = 10000
    if len(text) > max_total:
        text = text[:max_total]

    # Chia thành các đoạn nhỏ
    chunks = split_text_smart(text, CHUNK_SIZE)
    logger.info(f"TTS: {len(text)} chars -> {len(chunks)} chunks")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            audio_parts = []

            for i, chunk in enumerate(chunks):
                logger.info(f"TTS chunk {i+1}/{len(chunks)}: {len(chunk)} chars")
                audio_data = await _tts_single_chunk(client, chunk, voice)

                if audio_data:
                    audio_parts.append(audio_data)
                else:
                    logger.warning(f"Chunk {i+1} failed, skipping")

            if not audio_parts:
                logger.error("All TTS chunks failed")
                return None

            # Ghép các phần audio lại
            # FPT trả về MP3 — ghép đơn giản bằng cách nối bytes
            filename = f"{uuid.uuid4().hex}.mp3"
            audio_path = os.path.join(config.AUDIO_DIR, filename)

            with open(audio_path, "wb") as f:
                for part in audio_parts:
                    f.write(part)

            file_size = os.path.getsize(audio_path)
            logger.info(f"Audio saved: {audio_path} ({file_size} bytes, {len(audio_parts)} parts)")
            return audio_path

    except Exception as e:
        logger.error(f"TTS failed: {e}")
        return None


async def cleanup_audio(audio_path: str):
    """Delete temporary audio file after sending."""
    try:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            logger.debug(f"Cleaned up audio: {audio_path}")
    except Exception as e:
        logger.warning(f"Audio cleanup failed: {e}")
