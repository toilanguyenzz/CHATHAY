"""AI summarization with Gemini, optimized for interactive summaries."""

import json
import logging
from typing import Any

import google.generativeai as genai
from PIL import Image

from config import config

logger = logging.getLogger(__name__)

genai.configure(api_key=config.GEMINI_API_KEY)

QUOTA_MESSAGE = "He thong AI dang het quota tam thoi. Ban vui long thu lai sau khoang 1 phut nhe."
GENERIC_SUMMARY_ERROR = "Xin loi, toi khong the tom tat tai lieu nay luc nay. Ban vui long thu lai sau."
GENERIC_IMAGE_ERROR = "Xin loi, toi khong the doc noi dung trong anh luc nay. Ban vui long chup ro hon hoac thu lai sau."


def _get_model():
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )


def _is_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    return "429" in message or "quota exceeded" in message or "rate limit" in message


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _normalize_points(data: dict[str, Any]) -> dict[str, Any]:
    points = data.get("points", [])
    normalized_points: list[dict[str, str | int]] = []

    for index, point in enumerate(points[:5], start=1):
        title = str(point.get("title", f"Y chinh {index}")).strip()
        brief = str(point.get("brief", "")).strip()
        detail = str(point.get("detail", brief)).strip()
        normalized_points.append(
            {
                "index": index,
                "title": title,
                "brief": brief or detail[:140],
                "detail": detail or brief,
            }
        )

    while len(normalized_points) < 5:
        index = len(normalized_points) + 1
        normalized_points.append(
            {
                "index": index,
                "title": f"Y chinh {index}",
                "brief": "Khong co du lieu.",
                "detail": "Khong co du lieu.",
            }
        )

    return {
        "document_title": str(data.get("document_title", "Tai lieu")).strip() or "Tai lieu",
        "overview": str(data.get("overview", "")).strip(),
        "points": normalized_points,
    }


def _build_text_prompt(text: str) -> str:
    if len(text) > 30000:
        text = text[:30000] + "\n\n[Tai lieu da duoc cat ngan vi qua dai]"

    return f"""
Ban la tro ly AI tom tat tai lieu tieng Viet cho nguoi dung pho thong.

Hay doc tai lieu va tra ve DUY NHAT JSON hop le theo dung schema:
{{
  "document_title": "ten tai lieu hoac chu de chinh",
  "overview": "1-2 cau tong quan rat ngan gon",
  "points": [
    {{
      "title": "ten y chinh",
      "brief": "1 cau ngan gon, toi da 160 ky tu",
      "detail": "giai thich ky hon cho y nay, 3-5 cau, ro rang, cu the, de hieu"
    }}
  ]
}}

Yeu cau bat buoc:
- Phai co dung 5 phan tu trong mang points.
- Moi point phai la mot y chinh khac nhau va huu ich.
- brief phai rat ngan, de user nhin la hieu so bo.
- detail phai ro rang, co nhac toi so lieu, thoi han, ten rieng neu tai lieu co.
- Khong markdown, khong backtick, khong giai thich ngoai JSON.

Noi dung tai lieu:
{text}
""".strip()


def _build_image_prompt() -> str:
    return """
Hay doc noi dung trong anh va tra ve DUY NHAT JSON hop le theo schema:
{
  "document_title": "chu de chinh cua anh",
  "overview": "1-2 cau tong quan rat ngan gon",
  "points": [
    {
      "title": "ten y chinh",
      "brief": "1 cau ngan gon, toi da 160 ky tu",
      "detail": "giai thich ky hon cho y nay, 3-5 cau, ro rang, cu the, de hieu"
    }
  ]
}

Yeu cau:
- Dung 5 y chinh.
- brief ngan, detail ro rang.
- Neu thay so tien, ngay thang, ten rieng thi dua vao detail.
- Khong markdown, khong backtick, khong giai thich ngoai JSON.
""".strip()


async def summarize_text_structured(text: str) -> dict[str, Any]:
    """Summarize extracted text into 5 interactive points."""
    try:
        response = _get_model().generate_content(_build_text_prompt(text))
        parsed = _extract_json(response.text)
        normalized = _normalize_points(parsed)
        logger.info("Structured summary generated: %s chars", len(response.text))
        return normalized
    except Exception as exc:
        logger.error("Structured text summarization failed: %s", exc)
        if _is_quota_error(exc):
            return {"error": QUOTA_MESSAGE}
        return {"error": GENERIC_SUMMARY_ERROR}


async def summarize_image_structured(image_path: str) -> dict[str, Any]:
    """Summarize image content into 5 interactive points."""
    try:
        image = Image.open(image_path)
        response = _get_model().generate_content([_build_image_prompt(), image])
        parsed = _extract_json(response.text)
        normalized = _normalize_points(parsed)
        logger.info("Structured image summary generated: %s chars", len(response.text))
        return normalized
    except Exception as exc:
        logger.error("Structured image summarization failed: %s", exc)
        if _is_quota_error(exc):
            return {"error": QUOTA_MESSAGE}
        return {"error": GENERIC_IMAGE_ERROR}


async def summarize_text(text: str, doc_type: str | None = None) -> str:
    result = await summarize_text_structured(text)
    if "error" in result:
        return str(result["error"])
    points = result["points"]
    return "\n".join(f"{point['index']}. {point['title']}: {point['detail']}" for point in points)


async def summarize_image(image_path: str) -> str:
    result = await summarize_image_structured(image_path)
    if "error" in result:
        return str(result["error"])
    points = result["points"]
    return "\n".join(f"{point['index']}. {point['title']}: {point['detail']}" for point in points)
