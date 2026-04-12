import os
import httpx
import logging
from config import config

logger = logging.getLogger(__name__)

async def speech_to_text(audio_path: str) -> str:
    """
    Chuyển đổi file âm thanh thành văn bản sử dụng FPT.AI ASR.
    Hỗ trợ gửi file audio trực tiếp.
    """
    if not config.FPT_AI_API_KEY:
        logger.error("FPT_AI_API_KEY is not set.")
        return ""

    url = 'https://api.fpt.ai/hmi/asr/general'
    headers = {
        'api-key': config.FPT_AI_API_KEY
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(audio_path, 'rb') as f:
                payload = f.read()
            
            response = await client.post(url, headers=headers, content=payload)
            response.raise_for_status()
            
            data = response.json()
            # FPT ASR thường trả về {"hypotheses": [{"utterance": "nội dung..."}]}
            if "hypotheses" in data and len(data["hypotheses"]) > 0:
                result = data["hypotheses"][0].get("utterance", "")
                return result
            return ""
            
    except Exception as e:
        logger.error(f"FPT ASR error: {e}", exc_info=True)
        return ""
