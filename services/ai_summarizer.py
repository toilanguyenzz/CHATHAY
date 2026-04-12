"""AI summarization with Gemini."""

import logging

import google.generativeai as genai
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential

from config import config
from prompts import DETECT_TYPE_PROMPT, PROMPTS, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

genai.configure(api_key=config.GEMINI_API_KEY)

QUOTA_MESSAGE = (
    "❌ He thong AI dang het quota tom tat tam thoi. "
    "Ban vui long thu lai sau khoang 1 phut nhe."
)
GENERIC_SUMMARY_ERROR = (
    "❌ Xin loi, toi khong the tom tat tai lieu nay luc nay. "
    "Ban vui long thu lai sau."
)
GENERIC_IMAGE_ERROR = (
    "❌ Xin loi, toi khong the doc noi dung trong anh luc nay. "
    "Ban vui long chup ro hon hoac thu lai sau."
)


def _get_model():
    """Build the Gemini model instance used for summarization."""
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            max_output_tokens=16384,
        ),
    )


def _is_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    return "429" in message or "quota exceeded" in message or "rate limit" in message


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def detect_document_type(text: str) -> str:
    """Auto-detect the document type from a short preview."""
    try:
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config=genai.GenerationConfig(max_output_tokens=100),
        )
        preview = text[:1000]
        prompt = DETECT_TYPE_PROMPT.format(content_preview=preview)

        response = model.generate_content(prompt)
        doc_type = response.text.strip().lower()

        valid_types = {"contract", "medical", "administrative", "education", "general"}
        if doc_type in valid_types:
            logger.info("Document type detected: %s", doc_type)
            return doc_type

        logger.warning("Unknown doc type '%s', defaulting to 'general'", doc_type)
        return "general"

    except Exception as exc:
        logger.error("Document type detection failed: %s", exc)
        return "general"


async def summarize_text(text: str, doc_type: str | None = None) -> str:
    """Summarize extracted text using Gemini."""
    try:
        # Bỏ auto-detect để tiết kiệm request (giảm 50% token)
        doc_type = "general"

        prompt_template = PROMPTS.get(doc_type, PROMPTS["general"])
        if len(text) > 30000:
            text = text[:30000] + "\n\n[... Tai lieu da duoc cat ngan vi qua dai ...]"

        prompt = prompt_template.format(content=text)
        model = _get_model()
        response = model.generate_content(prompt)
        summary = response.text.strip()
        logger.info("Summary generated: %s chars, type=%s", len(summary), doc_type)

        return summary

    except Exception as exc:
        logger.error("Summarization failed: %s", exc)
        if _is_quota_error(exc):
            return QUOTA_MESSAGE
        return GENERIC_SUMMARY_ERROR


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def summarize_image(image_path: str) -> str:
    """Summarize content from an image using Gemini vision."""
    try:
        model = _get_model()
        image = Image.open(image_path)
        prompt = (
            "Hay doc noi dung trong anh nay va tom tat thanh dung 5 y chinh. "
            "Moi y viet 3-5 cau, giai thich day du chi tiet. "
            "Trich dan cu the cac con so, ngay thang va ten rieng neu co. "
            "Viet bang tieng Viet don gian, de hieu."
        )

        response = model.generate_content([prompt, image])
        summary = response.text.strip()
        logger.info("Image summary generated: %s chars", len(summary))
        return summary

    except Exception as exc:
        logger.error("Image summarization failed: %s", exc)
        if _is_quota_error(exc):
            return QUOTA_MESSAGE
        return GENERIC_IMAGE_ERROR
