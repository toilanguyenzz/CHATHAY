"""FPT.AI Text-to-Speech service."""

import asyncio
import logging
import os
import uuid

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import config

logger = logging.getLogger(__name__)

FPT_TTS_URL = "https://api.fpt.ai/hmi/tts/v5"
CHUNK_SIZE = 450
DOWNLOAD_ATTEMPTS = 12


def split_text_smart(text: str, max_chars: int = CHUNK_SIZE) -> list[str]:
    """Split long text into smaller chunks for FPT TTS."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        cut_at = -1
        for sep in [". ", ".\n", "? ", "! ", ";\n", "; ", ",\n", ", "]:
            pos = remaining[:max_chars].rfind(sep)
            if pos > cut_at:
                cut_at = pos + len(sep)

        if cut_at <= 0:
            cut_at = remaining[:max_chars].rfind(" ")
        if cut_at <= 0:
            cut_at = max_chars

        chunk = remaining[:cut_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut_at:].strip()

    return chunks


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _tts_single_chunk(client: httpx.AsyncClient, text: str, voice: str) -> bytes | None:
    """Generate one TTS chunk and download the resulting audio bytes."""
    try:
        response = await client.post(
            FPT_TTS_URL,
            headers={
                "api-key": config.FPT_AI_API_KEY,
                "speed": "0",
                "voice": voice,
            },
            data=text.encode("utf-8"),
        )

        if response.status_code != 200:
            logger.error("FPT.AI TTS failed: %s %s", response.status_code, response.text)
            return None

        result = response.json()
        audio_url = result.get("async")
        if not audio_url:
            logger.error("No audio URL in response: %s", result)
            return None

        # FPT can return the async URL before the file is ready.
        for attempt in range(DOWNLOAD_ATTEMPTS):
            await asyncio.sleep(min(2 + attempt, 8))
            audio_response = await client.get(audio_url)
            if audio_response.status_code == 200 and len(audio_response.content) > 100:
                return audio_response.content
            if audio_response.status_code not in {202, 404}:
                logger.warning(
                    "Unexpected TTS download status %s on attempt %s",
                    audio_response.status_code,
                    attempt + 1,
                )

        logger.error("Audio download failed after retries: %s", audio_url)
        return None

    except Exception as exc:
        logger.error("TTS chunk error: %s", exc)
        return None


async def text_to_speech(text: str, voice: str | None = None) -> str | None:
    """Convert text to Vietnamese speech using FPT.AI TTS."""
    if not config.FPT_AI_API_KEY:
        logger.warning("FPT_AI_API_KEY not set, skipping TTS")
        return None

    voice = voice or config.FPT_AI_VOICE
    if len(text) > 10000:
        text = text[:10000]

    chunks = split_text_smart(text, CHUNK_SIZE)
    logger.info("TTS: %s chars -> %s chunks", len(text), len(chunks))

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            audio_parts: list[bytes] = []

            for index, chunk in enumerate(chunks, start=1):
                logger.info("TTS chunk %s/%s: %s chars", index, len(chunks), len(chunk))
                audio_data = await _tts_single_chunk(client, chunk, voice)
                if audio_data:
                    audio_parts.append(audio_data)
                else:
                    logger.warning("Chunk %s failed, skipping", index)

            if not audio_parts:
                logger.error("All TTS chunks failed")
                return None

            filename = f"{uuid.uuid4().hex}.mp3"
            audio_path = os.path.join(config.AUDIO_DIR, filename)

            with open(audio_path, "wb") as output_file:
                for part in audio_parts:
                    output_file.write(part)

            file_size = os.path.getsize(audio_path)
            logger.info(
                "Audio saved: %s (%s bytes, %s parts)",
                audio_path,
                file_size,
                len(audio_parts),
            )
            return audio_path

    except Exception as exc:
        logger.error("TTS failed: %s", exc)
        return None


async def cleanup_audio(audio_path: str):
    """Delete temporary audio file after sending."""
    try:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            logger.debug("Cleaned up audio: %s", audio_path)
    except Exception as exc:
        logger.warning("Audio cleanup failed: %s", exc)
