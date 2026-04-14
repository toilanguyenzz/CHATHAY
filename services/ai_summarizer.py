"""AI summarization with Gemini — Zero-Waste 4-Layer Strategy.

Layer 1: CACHE   — MD5 content hash → skip API if already summarized
Layer 2: CUT     — Smart truncation 30K → 5K chars (head+mid+tail)
Layer 3: CASCADE — Model routing: flash-lite for short, flash for long
Layer 4: ROTATE  — Multi-key round-robin across Google projects
"""

import hashlib
import json
import logging
import asyncio
import time
from collections import OrderedDict
from typing import Any

import google.generativeai as genai
from PIL import Image

from config import config

logger = logging.getLogger(__name__)

# ===== LAYER 4: MULTI-KEY ROTATION =====

_api_keys: list[str] = [k for k in [
    config.GEMINI_API_KEY,
    getattr(config, "GEMINI_API_KEY_2", ""),
    getattr(config, "GEMINI_API_KEY_3", ""),
] if k]

_current_key_index = 0
_key_lock = asyncio.Lock()


def _rotate_key() -> str:
    """Round-robin qua các API keys. Nếu chỉ có 1 key thì dùng key đó."""
    global _current_key_index
    if not _api_keys:
        return config.GEMINI_API_KEY
    key = _api_keys[_current_key_index % len(_api_keys)]
    _current_key_index += 1
    return key


def _configure_next_key():
    """Cấu hình genai với key tiếp theo trong vòng xoay."""
    key = _rotate_key()
    genai.configure(api_key=key)
    return key


# Init with first key
genai.configure(api_key=_api_keys[0] if _api_keys else config.GEMINI_API_KEY)

# ===== LAYER 1: CONTENT HASH CACHE =====

CACHE_MAX_SIZE = 200


class SummaryCache:
    """LRU cache dựa trên MD5 hash nội dung. Tránh gọi AI trùng lặp."""

    def __init__(self, max_size: int = CACHE_MAX_SIZE):
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> dict[str, Any] | None:
        key = self._hash(text)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            logger.info("CACHE HIT [%s hits / %s misses, %s entries]",
                        self._hits, self._misses, len(self._cache))
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, text: str, result: dict[str, Any]):
        key = self._hash(text)
        self._cache[key] = result
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    @property
    def stats(self) -> str:
        total = self._hits + self._misses
        rate = (self._hits / total * 100) if total > 0 else 0
        return f"{self._hits}/{total} ({rate:.0f}% hit rate)"


_text_cache = SummaryCache()
_image_cache = SummaryCache()

# ===== CONSTANTS =====

QUOTA_MESSAGE = "He thong AI dang het quota tam thoi. Ban vui long thu lai sau khoang 1 phut nhe."
GENERIC_SUMMARY_ERROR = "Xin loi, toi khong the tom tat tai lieu nay luc nay. Ban vui long thu lai sau."
GENERIC_IMAGE_ERROR = "Xin loi, toi khong the doc noi dung trong anh luc nay. Ban vui long chup ro hon hoac thu lai sau."

# Rate limiting (Removed: User is now on Tier 1 Postpay with 1000 RPM)
# gemini_lock = asyncio.Lock()

# ===== LAYER 3: MODEL CASCADE =====

MODEL_LIGHT = "gemini-2.5-flash-lite"   # Nhẹ nhất, quota riêng
MODEL_STANDARD = "gemini-2.5-flash"      # Mạnh hơn, quota riêng
LIGHT_THRESHOLD = 2000                   # Dưới 2000 ký tự → dùng model nhẹ


def _get_model(text_length: int = 0) -> genai.GenerativeModel:
    """Chọn model phù hợp theo độ dài input."""
    model_name = MODEL_LIGHT if text_length < LIGHT_THRESHOLD else MODEL_STANDARD
    logger.info("Model selected: %s (input ~%s chars)", model_name, text_length)
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=2048,  # Giảm từ 4096 → 2048 (JSON 5 ý không cần nhiều)
            response_mime_type="application/json",
        ),
    )


def _is_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    return "429" in message or "quota exceeded" in message or "rate limit" in message


def _is_model_not_found(error: Exception) -> bool:
    message = str(error).lower()
    return "404" in message or "not found" in message or "not supported" in message


# ===== LAYER 2: SMART TRUNCATION =====

def _smart_truncate(text: str, max_total: int = 5000) -> str:
    """Cắt thông minh: giữ đầu + giữa + cuối thay vì cắt cứng.
    
    Lý do: Đầu tài liệu chứa tiêu đề + giới thiệu (~40% info).
    Cuối tài liệu chứa kết luận + tóm tắt (~30% info).
    Giữa chứa nội dung chi tiết (~30% info).
    """
    if len(text) <= max_total:
        return text

    head_size = int(max_total * 0.4)   # 2000 ký tự đầu
    mid_size = int(max_total * 0.3)    # 1500 ký tự giữa
    tail_size = int(max_total * 0.3)   # 1500 ký tự cuối

    head = text[:head_size]

    mid_start = (len(text) - mid_size) // 2
    mid = text[mid_start:mid_start + mid_size]

    tail = text[-tail_size:]

    truncated = (
        f"{head}\n\n"
        f"[...phan giua tai lieu...]\n\n"
        f"{mid}\n\n"
        f"[...phan cuoi tai lieu...]\n\n"
        f"{tail}"
    )

    logger.info("Smart truncation: %s → %s chars (saved %s%%)",
                len(text), len(truncated), 
                round((1 - len(truncated) / len(text)) * 100))
    return truncated


# ===== JSON HELPERS =====

def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            # Skip the first line (e.g. ```json) and the last line (```)
            # Find index of first ``` and last ```
            start_idx = text.find("\n")
            end_idx = text.rfind("```")
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                text = text[start_idx:end_idx].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
        
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("JSON Decode error: %s. Text: %s", e, text)
        # Attempt to repair common JSON errors if possible, but mainly raise
        raise ValueError(f"AI trả về định dạng không chuẩn (JSONDecodeError): {e}")


def _normalize_points(data: dict[str, Any]) -> dict[str, Any]:
    points = data.get("points", [])
    normalized_points: list[dict[str, str | int]] = []

    for index, point in enumerate(points[:5], start=1):
        title = str(point.get("title", f"Y chinh {index}")).strip()
        brief = str(point.get("brief", "")).strip()
        detail = str(point.get("detail", brief)).strip()
        normalized_points.append({
            "index": index,
            "title": title,
            "brief": brief or detail[:140],
            "detail": detail or brief,
        })

    while len(normalized_points) < 5:
        index = len(normalized_points) + 1
        normalized_points.append({
            "index": index,
            "title": f"Y chinh {index}",
            "brief": "Khong co du lieu.",
            "detail": "Khong co du lieu.",
        })

    return {
        "document_title": str(data.get("document_title", "Tai lieu")).strip() or "Tai lieu",
        "overview": str(data.get("overview", "")).strip(),
        "points": normalized_points,
    }


# ===== PROMPTS (tối giản hóa) =====

def _build_text_prompt(text: str) -> str:
    text = _smart_truncate(text)
    return f"""Tom tat tai lieu thanh JSON:
{{"document_title":"ten","overview":"1-2 cau","points":[{{"title":"y chinh","brief":"1 cau <160 ky tu","detail":"3-5 cau giai thich"}}]}}
Bat buoc 5 points. Neu co so lieu/ngay thang/ten rieng thi dua vao detail. Chi tra ve JSON.
LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT ĐƠN GIẢN, DÙ TÀI LIỆU GỐC LÀ TIẾNG GÌ.

{text}"""


def _build_image_prompt() -> str:
    return """Doc anh, tra ve JSON:
{"document_title":"chu de","overview":"1-2 cau","points":[{"title":"y chinh","brief":"1 cau <160 ky tu","detail":"3-5 cau giai thich"}]}
Bat buoc 5 points. Dua so lieu/ngay thang/ten rieng vao detail. Chi tra ve JSON.
LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT ĐƠN GIẢN, DÙ TÀI LIỆU GỐC LÀ TIẾNG GÌ."""


# ===== CORE API CALLS =====

async def _call_gemini_with_fallback(content, text_length: int = 0) -> str:
    """Gọi Gemini với fallback: nếu model chính 404 → thử model khác."""
    models_to_try = [
        MODEL_LIGHT if text_length < LIGHT_THRESHOLD else MODEL_STANDARD,
        MODEL_STANDARD,  # fallback 1
        "gemini-1.5-flash-8b",  # fallback 2
        "gemini-1.5-flash",  # fallback 3
    ]
    # Deduplicate while preserving order
    seen = set()
    unique_models = []
    for m in models_to_try:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)

    last_error = None
    for model_name in unique_models:
        try:
            _configure_next_key()
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                ),
            )
            response = model.generate_content(content)
            logger.info("Gemini OK: model=%s, response=%s chars", model_name, len(response.text))
            return response.text
        except Exception as exc:
            last_error = exc
            if _is_model_not_found(exc):
                logger.warning("Model %s not available, trying next: %s", model_name, exc)
                continue
            if _is_quota_error(exc):
                logger.warning("Quota hit on %s, trying next key/model: %s", model_name, exc)
                continue
            raise  # Other errors propagate

    raise last_error  # All models failed


# ===== PUBLIC API =====

async def summarize_text_structured(text: str) -> dict[str, Any]:
    """Summarize text → 5 interactive points. Uses cache + smart truncation."""
    # Layer 1: Check cache
    cached = _text_cache.get(text)
    if cached:
        return cached

    try:
        prompt = _build_text_prompt(text)
        response_text = await _call_gemini_with_fallback(prompt, len(text))
        parsed = _extract_json(response_text)
        normalized = _normalize_points(parsed)
        logger.info("Summary generated: %s chars, cache stats: %s",
                    len(response_text), _text_cache.stats)

        # Layer 1: Store in cache
        _text_cache.put(text, normalized)
        return normalized

    except Exception as exc:
            logger.error("Summarization failed: %s", exc)
            if _is_quota_error(exc):
                return {"error": QUOTA_MESSAGE}
            
            error_msg = str(exc)
            # Dùng thẳng lỗi để hiển thị tạm cho dev sửa
            return {"error": f"Lỗi tạo tóm tắt: {error_msg}. Vui lòng thử lại!"}


async def summarize_image_structured(image_path: str) -> dict[str, Any]:
    """Summarize image → 5 interactive points. Uses cache by file path."""
    # Layer 1: Check cache (by image path)
    cached = _image_cache.get(image_path)
    if cached:
        return cached

    try:
        image = Image.open(image_path)
        response_text = await _call_gemini_with_fallback(
            [_build_image_prompt(), image], text_length=500
        )
        parsed = _extract_json(response_text)
        normalized = _normalize_points(parsed)
        logger.info("Image summary generated: %s chars, cache stats: %s",
                    len(response_text), _image_cache.stats)

        _image_cache.put(image_path, normalized)
        return normalized

    except Exception as exc:
            logger.error("Image summarization failed: %s", exc)
            if _is_quota_error(exc):
                return {"error": QUOTA_MESSAGE}
            return {"error": GENERIC_IMAGE_ERROR}


# ===== BACKWARD COMPATIBLE WRAPPERS =====

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
