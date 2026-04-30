"""AI summarization with Gemini — Zero-Waste 4-Layer Strategy + OCR + Doc Classification.

Layer 1: CACHE   — MD5 content hash → skip API if already summarized
Layer 2: CUT     — Smart truncation 30K → 5K chars (head+mid+tail)
Layer 3: CASCADE — Model routing: flash-lite for short, flash for long
Layer 4: ROTATE  — Multi-key round-robin across Google projects

NEW (T4/2026):
  - OCR: Trích xuất text thô từ ảnh (cạnh tranh Zalo OCR built-in)
  - DOC TYPE: Phân loại tài liệu (hóa đơn, hợp đồng, giấy tờ hành chính...)
"""

import hashlib
import json
import logging
import asyncio
import re
from collections import OrderedDict
from typing import Any

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from PIL import Image
import httpx

from config import config
from prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Safety settings for Gemini
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# ═══════════════════════════════════════════════════════════════
# LAYER 4: MULTI-KEY ROTATION
# ═══════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════
# LAYER 1: CONTENT HASH CACHE
# ═══════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

QUOTA_MESSAGE = "Hệ thống AI đang hết quota tạm thời. Bạn vui lòng thử lại sau khoảng 1 phút nhé."
GENERIC_SUMMARY_ERROR = "Xin lỗi, tôi không thể tóm tắt tài liệu này lúc này. Bạn vui lòng thử lại sau."
GENERIC_IMAGE_ERROR = "Xin lỗi, tôi không thể đọc nội dung trong ảnh lúc này. Bạn vui lòng chụp rõ hơn hoặc thử lại sau."
MIN_SUMMARY_POINTS = 3
MAX_SUMMARY_POINTS = 15
DEFAULT_IMAGE_TARGET_POINTS = 4

# Document type labels (Vietnamese)
DOC_TYPE_LABELS = {
    "invoice": "🧾 Hóa đơn",
    "contract": "📄 Hợp đồng",
    "admin": "📋 Giấy tờ hành chính",
    "medical": "🏥 Tài liệu y tế",
    "education": "🎓 Tài liệu giáo dục",
    "password": "🔐 Thông tin đăng nhập",
    "task_assignment": "📋 Phân công nhiệm vụ",
    "bulk_accounts": "🗂️ Danh sách tài khoản",
    "photo": "📷 Ảnh chụp",
    "spreadsheet": "📊 Bảng tính",
    "general": "📝 Tài liệu",
}

# ═══════════════════════════════════════════════════════════════
# LAYER 3: MODEL CASCADE
# ═══════════════════════════════════════════════════════════════

MODEL_LIGHT = "gemini-2.5-flash"         # Dùng flash cho tất cả (chất lượng tốt, giá rẻ)
MODEL_STANDARD = "gemini-2.5-flash"      # Model chính
LIGHT_THRESHOLD = 0                      # Luôn dùng model standard


def _is_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    return "429" in message or "quota exceeded" in message or "rate limit" in message


def _is_model_not_found(error: Exception) -> bool:
    message = str(error).lower()
    return "404" in message or "not found" in message or "not supported" in message


# ═══════════════════════════════════════════════════════════════
# LAYER 2: SMART TRUNCATION
# ═══════════════════════════════════════════════════════════════

def _smart_truncate(text: str, max_total: int = 100000) -> str:
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
        f"[...phần giữa tài liệu...]\n\n"
        f"{mid}\n\n"
        f"[...phần cuối tài liệu...]\n\n"
        f"{tail}"
    )

    logger.info("Smart truncation: %s → %s chars (saved %s%%)",
                len(text), len(truncated),
                round((1 - len(truncated) / len(text)) * 100))
    return truncated


# ═══════════════════════════════════════════════════════════════
# JSON HELPERS
# ═══════════════════════════════════════════════════════════════

def _repair_json(text: str) -> str:
    """Sửa chữa JSON bị cắt cụt từ Gemini.

    Xử lý các trường hợp:
    - Unterminated string (thiếu dấu ngoặc kép đóng)
    - Thiếu dấu ] hoặc } ở cuối
    - Cắt giữa chừng một object trong mảng
    """
    text = text.strip()
    if not text:
        return text

    # Bước 1: Đếm ngoặc mở/đóng
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')

    # Nếu JSON đã hợp lệ, trả về ngay
    if open_braces == close_braces and open_brackets == close_brackets:
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass  # Tiếp tục sửa

    # Bước 2: Sửa chuỗi bị cắt cụt (unterminated string)
    in_string = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '\\' and in_string:
            i += 2  # Bỏ qua ký tự escape
            continue
        if ch == '"':
            in_string = not in_string
        i += 1

    # Nếu đang mở string (số dấu " lẻ), đóng lại
    if in_string:
        text = text + '"'
        logger.info("JSON repair: closed unterminated string")

    # Bước 3: Thử thêm ngoặc đóng
    try:
        json.loads(text + ']' * (open_brackets - close_brackets) + '}' * (open_braces - close_braces))
        text = text + ']' * (open_brackets - close_brackets) + '}' * (open_braces - close_braces)
        logger.info("JSON repair: added missing brackets/braces")
        return text
    except json.JSONDecodeError:
        pass

    # Bước 4: Phương án mạnh hơn — cắt bỏ element cuối nếu bị lỗi
    for cut_char in [',', '{']:
        last_cut = text.rfind(cut_char)
        if last_cut > 0:
            candidate = text[:last_cut]
            open_b = candidate.count('{')
            close_b = candidate.count('}')
            open_sq = candidate.count('[')
            close_sq = candidate.count(']')
            suffix = ']' * max(0, open_sq - close_sq) + '}' * max(0, open_b - close_b)
            try:
                result = candidate + suffix
                json.loads(result)
                logger.info("JSON repair: truncated broken tail and closed (cut at '%s')", cut_char)
                return result
            except json.JSONDecodeError:
                continue

    return text  # Trả về nguyên bản nếu không sửa được


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            start_idx = text.find("\n")
            end_idx = text.rfind("```")
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                text = text[start_idx:end_idx].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    elif start >= 0:
        # Không tìm thấy dấu } → JSON bị cắt cụt hoàn toàn
        text = text[start:]

    # Thử parse trực tiếp trước
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Thử sửa chữa JSON
    repaired = _repair_json(text)
    try:
        result = json.loads(repaired)
        logger.info("JSON repaired successfully! Original: %s chars, Repaired: %s chars",
                    len(text), len(repaired))
        return result
    except json.JSONDecodeError as e:
        logger.error("JSON repair failed. Original text (%s chars): %s", len(text), text[:500])
        raise ValueError(f"AI trả về JSON bị lỗi không sửa được: {e}")


# ═══════════════════════════════════════════════════════════════
# TEXT HELPERS
# ═══════════════════════════════════════════════════════════════

def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clip_text(value: str, max_len: int = 160) -> str:
    value = _normalize_whitespace(value)
    if len(value) <= max_len:
        return value
    return value[: max_len - 3].rstrip() + "..."


# ═══════════════════════════════════════════════════════════════
# SMART POINT ESTIMATION
# ═══════════════════════════════════════════════════════════════

def _estimate_target_points(text: str) -> int:
    """Ước tính số ý phù hợp dựa trên độ phức tạp tài liệu."""
    normalized = _normalize_whitespace(text)
    length = len(normalized)
    paragraph_count = len([block for block in re.split(r"\n\s*\n", text) if block.strip()])
    bullet_count = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[\.\)])", text))
    heading_count = len(re.findall(
        r"(?im)^\s*(?:[A-Z0-9IVX]+\s*[\.\):\-]|Dieu\s+\d+|Điều\s+\d+|Muc\s+\d+|Mục\s+\d+|Phan\s+\d+|Phần\s+\d+|Section\s+\d+|Chapter\s+\d+)",
        text,
    ))
    sentence_count = len(re.findall(r"[.!?…]+", text))
    digit_count = len(re.findall(r"\d", text))

    score = 0
    for threshold in (700, 1600, 3200, 6000, 9000, 15000, 25000, 40000):
        if length >= threshold:
            score += 1
    if paragraph_count >= 6:
        score += 1
    if paragraph_count >= 12:
        score += 1
    if paragraph_count >= 20:
        score += 1
    if bullet_count >= 4:
        score += 1
    if bullet_count >= 8:
        score += 1
    if heading_count >= 3:
        score += 1
    if heading_count >= 5:
        score += 1
    if sentence_count >= 18:
        score += 1
    if sentence_count >= 40:
        score += 1
    if digit_count >= 30:
        score += 1

    return max(
        MIN_SUMMARY_POINTS,
        min(MAX_SUMMARY_POINTS, 5 + min(score, MAX_SUMMARY_POINTS - MIN_SUMMARY_POINTS)),
    )


# ═══════════════════════════════════════════════════════════════
# POINT NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def _normalize_points(data: dict[str, Any], target_points: int | None = None) -> dict[str, Any]:
    """Chuẩn hóa kết quả AI: đảm bảo đúng format, loại trùng, giữ OCR/doc_type."""
    points = data.get("points", [])
    normalized_points: list[dict[str, str | int]] = []
    seen_signatures: set[str] = set()
    desired_points = max(
        MIN_SUMMARY_POINTS,
        min(MAX_SUMMARY_POINTS, target_points or len(points) or MIN_SUMMARY_POINTS),
    )

    for point in points:
        if len(normalized_points) >= desired_points:
            break

        title = _normalize_whitespace(str(point.get("title", "")))
        brief = _normalize_whitespace(str(point.get("brief", "")))
        detail = _normalize_whitespace(str(point.get("detail", brief)))

        if not detail and brief:
            detail = brief
        if not brief and detail:
            brief = detail
        if not title:
            title = _clip_text(brief or detail, 72)
        if not title:
            continue

        brief = _clip_text(brief or detail or title, 160)
        detail = detail or brief or title
        signature = f"{title.lower()}|{brief.lower()}|{detail[:120].lower()}"
        if signature in seen_signatures:
            continue

        seen_signatures.add(signature)
        normalized_points.append({
            "index": len(normalized_points) + 1,
            "title": title,
            "brief": brief,
            "detail": detail,
        })

    if not normalized_points:
        overview = _normalize_whitespace(str(data.get("overview", "")))
        fallback = overview or "Chưa trích xuất được nội dung nổi bật."
        normalized_points.append({
            "index": 1,
            "title": "Tổng quan",
            "brief": _clip_text(fallback, 160),
            "detail": fallback,
        })

    result = {
        "document_title": _normalize_whitespace(str(data.get("document_title", "Tài liệu"))) or "Tài liệu",
        "overview": _normalize_whitespace(str(data.get("overview", ""))),
        "points": normalized_points,
        "point_count": len(normalized_points),
    }

    # Giữ lại document_type
    doc_type = str(data.get("document_type", "")).strip().lower()
    if doc_type and doc_type in DOC_TYPE_LABELS:
        result["document_type"] = doc_type

    # Action items (việc cần làm)
    action_items = data.get("action_items")
    if action_items and isinstance(action_items, list):
        result["action_items"] = [_normalize_whitespace(str(a)) for a in action_items if str(a).strip()][:4]

    # Suggested questions (gợi ý câu hỏi)
    suggested_questions = data.get("suggested_questions")
    if suggested_questions and isinstance(suggested_questions, list):
        result["suggested_questions"] = [_normalize_whitespace(str(q)) for q in suggested_questions if str(q).strip()][:3]

    return result


# ═══════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════

def _build_text_prompt(text: str, target_points: int) -> str:
    """Prompt tóm tắt text — chất lượng cao, có action items và gợi ý câu hỏi."""
    text = _smart_truncate(text)

    # Detect Excel source → add specialized hint
    excel_hint = ""
    if "[Excel:" in text:
        excel_hint = """
🎯 ĐÂY LÀ DỮ LIỆU TỪ FILE EXCEL (BẢNG TÍNH):
- Phân tích SỐ LIỆU cụ thể: tổng, trung bình, min, max, so sánh giữa các cột/hàng.
- Nếu có nhiều sheet, so sánh dữ liệu giữa các sheet.
- suggested_questions PHẢI là câu hỏi phân tích số liệu (tính tổng, so sánh, tìm max/min, xu hướng...).
- Ví dụ: "Tổng doanh thu tháng nào cao nhất?", "So sánh chi phí Q1 và Q2?", "Ai có lương cao nhất?"
"""

    return f"""Hãy đọc kỹ toàn bộ tài liệu và phân tích thật chi tiết. Trả về JSON:

{{"document_title": "Tên tài liệu", "overview": "2-3 câu tổng quan ngắn gọn", "document_type": "general", "points": [{{"title": "Tiêu đề", "brief": "Tóm tắt 1 câu dưới 160 ký tự", "detail": "Đoạn văn 4-8 câu cực kỳ chi tiết"}}], "action_items": ["Việc cần làm 1", "Việc cần làm 2"], "suggested_questions": ["Câu hỏi gợi ý 1?", "Câu hỏi gợi ý 2?"]}}

⚠️ NGÔN NGỮ BẮT BUỘC: TOÀN BỘ output phải bằng TIẾNG VIỆT CÓ DẤU.
- TUYỆT ĐỐI KHÔNG dùng tiếng Trung Quốc (中文), tiếng Nhật, tiếng Hàn trong output.
- Nếu tài liệu gốc có tiếng Trung/tiếng nước ngoài → DỊCH SANG TIẾNG VIỆT.
- Ví dụ: 放弃 → "từ bỏ", 执行 → "thực hiện". KHÔNG giữ nguyên ký tự Trung Quốc.

QUY TẮC VIẾT:
1. Tiếng Việt CÓ DẤU, dễ hiểu, đi thẳng vào trọng tâm.
2. TRÍCH DẪN CỤ THỂ: con số, số tiền, ngày tháng, tên người, tên tổ chức.
3. CẤM nói chung chung kiểu "có nhiều quy định". PHẢI nêu cụ thể.
4. Thuật ngữ chuyên môn → giải thích ngay trong ngoặc.
5. "detail" PHẢI 4-8 câu, cực kỳ chi tiết với dữ kiện cụ thể.
6. Ưu tiên: số liệu → ngày tháng → tên riêng → việc cần làm → cảnh báo.

{excel_hint}

🎯 ACTION ITEMS (action_items):
- Rút ra 2-4 việc cụ thể người đọc CẦN LÀM sau khi đọc tài liệu này.
- Viết ngắn gọn, bắt đầu bằng động từ: "Nộp...", "Liên hệ...", "Kiểm tra...", "Lưu ý..."
- Nếu không có việc cần làm → ["Đọc và lưu lại để tham khảo khi cần"]

❓ SUGGESTED QUESTIONS (suggested_questions):
- Gợi ý 2-3 câu hỏi mà người đọc có thể MUỐN HỎI THÊM về tài liệu này.
- Ví dụ: "Khoản phạt chậm thanh toán tính như thế nào?", "Thuốc này có tác dụng phụ gì?"
- NẾU LÀ EXCEL/BẢNG TÍNH: ưu tiên câu hỏi phân tích số liệu như "Tổng doanh thu?", "Tháng nào cao nhất?", "So sánh giữa các cột?"

Số ý: từ {MIN_SUMMARY_POINTS} đến {MAX_SUMMARY_POINTS}, mục tiêu {target_points} ý.
Chỉ trả về JSON hợp lệ.

═════════════════════════════════
{text}"""


def _build_image_prompt(target_points: int = DEFAULT_IMAGE_TARGET_POINTS) -> str:
    """Prompt tóm tắt ảnh — chất lượng cao."""
    return f"""Hãy đọc kỹ nội dung trong ảnh. Trả về JSON:

{{"document_title": "Chủ đề", "overview": "2-3 câu tóm tắt", "document_type": "loại", "points": [{{"title": "Tiêu đề", "brief": "Tóm tắt 1 câu", "detail": "Đoạn văn 3-7 câu chi tiết"}}], "action_items": ["Việc cần làm"], "suggested_questions": ["Câu hỏi gợi ý?"]}}

PHÂN LOẠI (document_type): photo | invoice | contract | admin | medical | education | general

QUY TẮC:
1. Tiếng Việt CÓ DẤU, đi thẳng vào trọng tâm.
2. TRÍCH DẪN CỤ THỂ mọi con số, ngày tháng, tên riêng.
3. CẤM nói chung chung. "detail" PHẢI 3-7 câu chi tiết.
4. action_items: 2-3 việc cụ thể cần làm. Bắt đầu bằng động từ.
5. suggested_questions: 2-3 câu hỏi người đọc có thể muốn hỏi thêm.

Số ý: từ {MIN_SUMMARY_POINTS} đến 6, mục tiêu {target_points}.
Chỉ trả về JSON hợp lệ."""


def _build_ocr_only_prompt() -> str:
    """Prompt chỉ trích xuất text từ ảnh (OCR thuần, không tóm tắt)."""
    return """Trich xuat TOAN BO van ban nhin thay trong anh nay.

Quy tac:
- Giu nguyen format goc (xuong dong, khoang cach, tho luc)
- Neu co bang bieu, trinh bay bang ky tu | va -
- Neu co nhieu cot, trinh bay tung cot rieng
- KHONG giai thich, KHONG them gi, chi tra ve van ban thuan tuy
- Neu anh khong co text nao, tra ve: "(Ảnh không có văn bản)"
"""

def _contains_chinese(text: str) -> bool:
    """Detect if text contains significant Chinese characters (not Vietnamese).
    
    Vietnamese uses Latin script with diacritics, NOT CJK characters.
    If we see CJK chars, the model is outputting Chinese instead of Vietnamese.
    """
    if not text:
        return False
    # Count CJK Unified Ideographs (Chinese/Japanese/Korean characters)
    cjk_count = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff' or '\u3400' <= ch <= '\u4dbf')
    # Allow a tiny amount (might be in original doc quotes), flag if > 10 chars
    return cjk_count > 10


async def _call_deepseek(
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    max_tokens: int = 8192,
    response_json: bool = True,
) -> str:
    """Gọi DeepSeek V4 Flash API (OpenAI-compatible format)."""
    
    # Enforce Vietnamese output for DeepSeek (Chinese model tends to output Chinese)
    vn_enforcement = (
        "\n\n⚠️ CRITICAL LANGUAGE RULE: You MUST respond ENTIRELY in Vietnamese (tiếng Việt có dấu). "
        "DO NOT use Chinese (中文) characters anywhere in your response. "
        "DO NOT translate meanings into Chinese. "
        "If the source document contains Chinese text, translate it to Vietnamese. "
        "Every single word in your output must be Vietnamese or English (for proper nouns). "
        "违反此规则将导致严重错误。请只用越南语回答。"
    )
    enforced_system_prompt = system_prompt + vn_enforcement
    
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    
    body = {
        "model": config.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": enforced_system_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    
    if response_json:
        body["response_format"] = {"type": "json_object"}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{config.DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        result = data["choices"][0]["message"]["content"]
        
        # Post-processing: Detect Chinese output → reject and fallback to Gemini
        if _contains_chinese(result):
            logger.warning("DeepSeek returned Chinese text! Rejecting and falling back to Gemini.")
            raise ValueError("DeepSeek output contains Chinese characters — falling back to Gemini")
        
        return result


async def _call_with_smart_routing(
    content,
    text_length: int = 0,
    max_tokens: int = 8192,
    response_json: bool = True,
    force_gemini: bool = False,
    system_prompt: str | None = None,
) -> str:
    """Smart routing: DeepSeek cho text, Gemini cho ảnh."""
    _sys_prompt = system_prompt or SYSTEM_PROMPT
    
    # ── Nếu CÓ DeepSeek key VÀ KHÔNG bắt buộc Gemini → dùng DeepSeek ──
    if config.DEEPSEEK_API_KEY and not force_gemini:
        try:
            # content phải là string (text-only)
            if isinstance(content, str):
                result = await _call_deepseek(
                    prompt=content,
                    system_prompt=_sys_prompt,
                    max_tokens=max_tokens,
                    response_json=response_json,
                )
                logger.info("DeepSeek V4 Flash OK: %s chars", len(result))
                return result
        except httpx.HTTPStatusError as exc:
            logger.error("DeepSeek API Error (HTTP %s): %s. Auto-switching to Gemini...", exc.response.status_code, exc)
        except httpx.RequestError as exc:
            logger.error("DeepSeek Network Error: %s. Auto-switching to Gemini...", exc)
        except Exception as exc:
            logger.error("DeepSeek Unexpected Error: %s. Auto-switching to Gemini...", exc)
    
    # ── Fallback / Ảnh: dùng Gemini (nếu DeepSeek lỗi hoặc là ảnh) ──
    logger.info("Routing request to Gemini (Fallback/Vision)...")
    return await _call_gemini_with_fallback(
        content, text_length, max_tokens, response_json, system_prompt=_sys_prompt
    )



async def _call_gemini_with_fallback(
    content,
    text_length: int = 0,
    max_tokens: int = 8192,
    response_json: bool = True,
    system_prompt: str | None = None,
) -> str:
    """Gọi Gemini với fallback: nếu model chính 404 → thử model khác."""
    _sys_prompt = system_prompt or SYSTEM_PROMPT
    models_to_try = [
        MODEL_STANDARD,          # gemini-2.5-flash (chính)
        "gemini-2.0-flash",      # fallback duy nhất
    ]
    # Deduplicate while preserving order
    seen = set()
    unique_models = []
    for m in models_to_try:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)

    gen_config_kwargs = {
        "temperature": 0.2,
        "max_output_tokens": max_tokens,
    }
    if response_json:
        gen_config_kwargs["response_mime_type"] = "application/json"

    last_error = None
    for model_name in unique_models:
        try:
            _configure_next_key()
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=_sys_prompt,
                generation_config=genai.GenerationConfig(**gen_config_kwargs),
            )
            response = model.generate_content(
                content,
                safety_settings=SAFETY_SETTINGS,
            )
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


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

async def summarize_text_structured(text: str) -> dict[str, Any]:
    """Tóm tắt text → dynamic ý chính tương tác. Dùng cache + smart truncation."""
    # Layer 1: Check cache
    cached = _text_cache.get(text)
    if cached:
        return cached

    target_points = _estimate_target_points(text)
    logger.info("Smart summary target: %s points for %s chars", target_points, len(text))

    last_error_msg = ""
    for attempt in range(3):
        try:
            prompt = _build_text_prompt(text, target_points)
            response_text = await _call_with_smart_routing(prompt, len(text))
            parsed = _extract_json(response_text)
            normalized = _normalize_points(parsed, target_points)
            logger.info(
                "Summary generated: %s chars, cache stats: %s, attempt: %s",
                len(response_text), _text_cache.stats, attempt + 1,
            )

            # Layer 1: Store in cache
            _text_cache.put(text, normalized)

            # ADDED: Detect document mode for Study Mode routing
            from services.mode_detector import detect_mode
            mode_result = await detect_mode(text)
            # Normalize: "STUDY_MATERIAL" -> "education" (matches webhook buttons)
            normalized["document_type"] = "education" if mode_result["mode"] == "STUDY_MATERIAL" else "general"
            normalized["mode_confidence"] = mode_result["confidence"]

            return normalized

        except Exception as exc:
            logger.warning("Summarization attempt %s failed: %s", attempt + 1, exc)
            if _is_quota_error(exc):
                return {"error": QUOTA_MESSAGE}
            last_error_msg = str(exc)
            await asyncio.sleep(1)

    return {"error": f"Lỗi tạo tóm tắt sau 3 lần thử: {last_error_msg}. Vui lòng thử lại!"}


async def summarize_image_structured(image_path: str) -> dict[str, Any]:
    """Tóm tắt ảnh → ý chính + document_type. Dùng cache.

    Returns dict with keys:
        - document_title, overview, points, point_count (standard)
        - document_type: invoice|contract|admin|medical|education|photo|general
    
    Lưu ý: KHÔNG bao gồm OCR text (tiết kiệm token).
    Dùng extract_ocr_text() riêng khi user yêu cầu.
    """
    # Layer 1: Check cache
    cached = _image_cache.get(image_path)
    if cached:
        return cached

    target_points = DEFAULT_IMAGE_TARGET_POINTS
    last_error_msg = ""
    for attempt in range(3):
        try:
            image = Image.open(image_path)
            response_text = await _call_gemini_with_fallback(
                [_build_image_prompt(target_points), image],
                text_length=500,
                max_tokens=4096,
            )
            parsed = _extract_json(response_text)
            normalized = _normalize_points(parsed, target_points)
            logger.info(
                "Image summary: %s chars, type=%s, cache=%s, attempt=%s",
                len(response_text),
                normalized.get("document_type", "unknown"),
                _image_cache.stats,
                attempt + 1,
            )

            _image_cache.put(image_path, normalized)
            return normalized

        except Exception as exc:
            logger.warning("Image summarization attempt %s failed: %s", attempt + 1, exc)
            if _is_quota_error(exc):
                return {"error": QUOTA_MESSAGE}
            last_error_msg = str(exc)
            await asyncio.sleep(1)

    return {"error": f"Xin lỗi, không thể đọc ảnh lúc này. Chi tiết: {last_error_msg}"}


async def extract_ocr_text(image_path: str) -> str:
    """Trích xuất text thuần từ ảnh (OCR only, không tóm tắt).

    Dùng khi user muốn chỉ lấy text mà không cần phân tích.
    """
    try:
        image = Image.open(image_path)
        result = await _call_gemini_with_fallback(
            [_build_ocr_only_prompt(), image],
            text_length=500,
            max_tokens=4096,
            response_json=False,  # Trả về text thuần, không JSON
        )
        return result.strip() if result else "(Không trích xuất được text từ ảnh)"
    except Exception as exc:
        logger.error("OCR extraction failed: %s", exc)
        if _is_quota_error(exc):
            return "(Hệ thống đang hết quota, thử lại sau 1 phút)"
        return f"(Lỗi khi trích xuất text: {exc})"


async def summarize_pdf_images_structured(image_paths: list[str]) -> dict[str, Any]:
    """Tóm tắt PDF scan/handwritten bằng cách gửi ảnh các trang cho Gemini Vision.
    
    Dùng khi extract_text() trả về rỗng (PDF scan, chữ viết tay, PDF chỉ có ảnh).
    Gửi tối đa 10 trang ảnh cùng lúc để Gemini đọc.
    """
    if not image_paths:
        return {"error": "Không có trang nào để phân tích."}

    target_points = min(len(image_paths) + 3, MAX_SUMMARY_POINTS)
    
    prompt = f"""Hãy đọc kỹ TOÀN BỘ các trang tài liệu (dạng ảnh scan/chụp) bên dưới.
Tài liệu này có {len(image_paths)} trang. Trả về JSON:

{{"document_title": "Tên tài liệu", "overview": "2-3 câu tổng quan ngắn gọn", "document_type": "general", "points": [{{"title": "Tiêu đề", "brief": "Tóm tắt 1 câu", "detail": "Đoạn văn 4-8 câu cực kỳ chi tiết"}}]}}

QUY TẮC:
1. Tiếng Việt CÓ DẤU, dễ hiểu, đi thẳng vào trọng tâm.
2. TRÍCH DẪN CỤ THỂ: con số, ngày tháng, tên người, tên tổ chức.
3. Nếu có bảng biểu → trích xuất dữ liệu cụ thể.
4. Chữ viết tay khó đọc → ghi "(chữ viết tay khó đọc)" và đoán nghĩa.
5. "detail" PHẢI 4-8 câu, cực kỳ chi tiết.
6. CẤM nói chung chung.

Số ý: {MIN_SUMMARY_POINTS} đến {MAX_SUMMARY_POINTS}, mục tiêu {target_points}.
Chỉ trả về JSON hợp lệ."""

    last_error_msg = ""
    for attempt in range(3):
        try:
            # Mở tất cả ảnh
            images = [Image.open(path) for path in image_paths]
            content = [prompt] + images
            
            response_text = await _call_gemini_with_fallback(
                content,
                text_length=2000,  # Force standard model for multi-page
                max_tokens=8192,
            )
            parsed = _extract_json(response_text)
            normalized = _normalize_points(parsed, target_points)
            logger.info(
                "PDF scan summary: %s pages, %s chars response, type=%s, attempt=%s",
                len(image_paths),
                len(response_text),
                normalized.get("document_type", "unknown"),
                attempt + 1,
            )
            return normalized

        except Exception as exc:
            logger.warning("PDF scan summarization attempt %s failed: %s", attempt + 1, exc)
            if _is_quota_error(exc):
                return {"error": QUOTA_MESSAGE}
            last_error_msg = str(exc)
            await asyncio.sleep(1)

    return {"error": f"Không thể đọc file PDF scan sau 3 lần thử: {last_error_msg}"}


def get_doc_type_label(doc_type: str) -> str:
    """Lấy nhãn tiếng Việt cho loại tài liệu."""
    return DOC_TYPE_LABELS.get(doc_type, DOC_TYPE_LABELS["general"])


# ═══════════════════════════════════════════════════════════════
# BACKWARD COMPATIBLE WRAPPERS
# ═══════════════════════════════════════════════════════════════

async def summarize_text(text: str, doc_type: str | None = None) -> str:
    """Wrapper trả về string cho backward compatibility."""
    result = await summarize_text_structured(text)
    if "error" in result:
        return str(result["error"])

    lines: list[str] = []
    overview = result.get("overview", "")
    if overview:
        lines.append(f"Tổng quan: {overview}")
        lines.append("")

    points = result["points"]
    lines.append(f"{len(points)} ý nổi bật:")
    lines.extend(f"{point['index']}. {point['title']}: {point['detail']}" for point in points)
    return "\n".join(lines)


async def summarize_image(image_path: str) -> str:
    """Wrapper trả về string cho backward compatibility."""
    result = await summarize_image_structured(image_path)
    if "error" in result:
        return str(result["error"])

    lines: list[str] = []
    overview = result.get("overview", "")
    if overview:
        lines.append(f"Tổng quan: {overview}")
        lines.append("")

    points = result["points"]
    lines.append(f"{len(points)} ý nổi bật:")
    lines.extend(f"{point['index']}. {point['title']}: {point['detail']}" for point in points)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Q&A: ANSWER QUESTIONS ABOUT DOCUMENTS
# ═══════════════════════════════════════════════════════════════

async def answer_question_about_document(question: str, document_text: str, doc_title: str = "tài liệu") -> str:
    """Trả lời câu hỏi dựa trên nội dung tài liệu — chất lượng cao.

    Sử dụng full document text làm context, Gemini sẽ trả lời
    CHỈ dựa trên thông tin có trong tài liệu.
    """
    # Truncate smart nếu quá dài (giữ max 80K chars cho context window)
    doc_context = _smart_truncate(document_text, max_total=80000)

    prompt = f"""Bạn là trợ lý AI chuyên phân tích tài liệu. Người dùng đang hỏi về tài liệu "{doc_title}".

CÂU HỎI CỦA NGƯỜI DÙNG:
{question}

NỘI DUNG TÀI LIỆU:
{doc_context}

QUY TẮC TRẢ LỜI (BẮT BUỘC):
1. CHỈ trả lời dựa trên thông tin CÓ TRONG tài liệu. KHÔNG bịa đặt, KHÔNG thêm kiến thức ngoài.
2. TRÍCH DẪN CỤ THỂ: nêu rõ con số, ngày tháng, tên người, điều khoản, số tiền từ tài liệu.
3. Tiếng Việt CÓ DẤU, rõ ràng, dễ hiểu — như đang giải thích cho bạn bè.
4. Nếu câu hỏi KHÔNG liên quan đến nội dung tài liệu → trả lời: "Tôi không tìm thấy thông tin về điều này trong tài liệu."
5. Nếu thông tin chỉ có một phần → nêu rõ phần nào có, phần nào thiếu.
6. Trả lời đầy đủ nhưng gọn (3-8 câu). Đừng lặp lại câu hỏi.
7. Nếu có nhiều thông tin liên quan → tổ chức thành danh sách ngắn gọn.

Trả lời:"""

    try:
        response_text = await _call_with_smart_routing(
            prompt,
            text_length=len(doc_context),
            max_tokens=2048,
            response_json=False,  # Trả về text thuần, không JSON
        )
        return response_text.strip() if response_text else "Không thể trả lời câu hỏi lúc này. Thử lại nhé!"
    except Exception as exc:
        logger.error("Q&A answer failed: %s", exc)
        if _is_quota_error(exc):
            return QUOTA_MESSAGE
        return "Đã xảy ra lỗi khi phân tích. Vui lòng thử lại!"

