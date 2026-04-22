"""Zalo OA webhook server — CHAT HAY v2.0

Nâng cấp T4/2026:
  - OCR: Trích xuất text từ ảnh + gửi kèm bản tóm tắt
  - Document Classification: Phân loại tài liệu tự động
  - Clean code: Xóa toàn bộ hàm trùng lặp
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import config
from services.ai_summarizer import (
    summarize_image_structured,
    summarize_text_structured,
    extract_ocr_text,
    get_doc_type_label,
)
from services.document_parser import extract_text, get_file_type
from services.tts_service import cleanup_audio, text_to_speech
from services.token_store import load_tokens, save_tokens, get_token_info
from services.db_service import (
    save_vault_credential,
    get_vault_credential,
    list_vault_credentials,
    set_pending_action,
    get_pending_action,
    clear_pending_action,
)
from services.deadline_service import (
    save_deadlines_from_summary,
    get_user_deadlines,
    get_upcoming_deadlines,
    mark_deadline_done,
    format_deadline_list,
    format_deadline_saved_notice,
    update_user_interaction,
    get_pending_notifications,
    set_message_sender,
    start_reminder_scheduler,
    stop_reminder_scheduler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

ZALO_TEXT_LIMIT = 2900
ZALO_MAX_BUTTONS = 5
ZALO_PRIMARY_POINT_BUTTONS = 4
ZALO_SHOW_MORE_PAYLOAD = "XEM THEM"
ZALO_BACK_TO_SUMMARY_PAYLOAD = "XEM TOM TAT"

# ═══════════════════════════════════════════════════════════════
# TOKEN MANAGEMENT
# ═══════════════════════════════════════════════════════════════

# Load tokens: ưu tiên DB (đã refresh) > biến môi trường (lần đầu)
_env_access = os.getenv("ZALO_OA_ACCESS_TOKEN", "")
_env_refresh = os.getenv("ZALO_REFRESH_TOKEN", "")
ZALO_OA_ACCESS_TOKEN, ZALO_REFRESH_TOKEN = load_tokens(_env_access, _env_refresh)

# Nếu env có token mới hơn (lần deploy đầu tiên), lưu vào DB
if _env_access and ZALO_OA_ACCESS_TOKEN == _env_access:
    save_tokens(_env_access, _env_refresh)

logger.info("Loaded tokens — Access: %s chars, Refresh: %s chars",
            len(ZALO_OA_ACCESS_TOKEN), len(ZALO_REFRESH_TOKEN))

ZALO_OA_SECRET = os.getenv("ZALO_OA_SECRET", "")
ZALO_APP_SECRET = os.getenv("ZALO_APP_SECRET", ZALO_OA_SECRET)
ZALO_APP_ID = os.getenv("ZALO_APP_ID", "1534343952928885811")
ZALO_API_URL = "https://openapi.zalo.me/v3.0/oa"
ZALO_OAUTH_URL = "https://oauth.zaloapp.com/v4/oa/access_token"
ZALO_VERIFICATION_CODE = os.getenv(
    "ZALO_VERIFICATION_CODE",
    "VyM34AN4DmzorQGojDui9ZNWYXdPbbz5DZ0t",
)

# ═══════════════════════════════════════════════════════════════
# STATE
# ═══════════════════════════════════════════════════════════════

user_daily_usage: dict[str, dict[str, int | str]] = {}
latest_summary_by_user: dict[str, dict[str, Any]] = {}
last_image_url_by_user: dict[str, str] = {}  # Lưu URL ảnh gần nhất để trích xuất chữ khi cần
_token_lock = asyncio.Lock()

# Tối ưu chống spam: cooldown giữa các tin nhắn
user_cooldowns: dict[str, float] = {}
user_warnings: dict[str, float] = {}
COOLDOWN_SECONDS = 15

# ═══════════════════════════════════════════════════════════════
# TOKEN REFRESH (v3 — fix triệt để Invalid refresh token)
# ═══════════════════════════════════════════════════════════════

# Lưu timestamp lần refresh thành công gần nhất để tránh refresh trùng
_last_successful_refresh_time: float = 0.0
# Khoảng cách tối thiểu giữa 2 lần refresh (giây) — tránh race condition
_MIN_REFRESH_INTERVAL = 5.0
# Proactive refresh interval (giây) — refresh trước khi token hết hạn
_PROACTIVE_REFRESH_INTERVAL = 30 * 60  # 30 phút


async def _sync_tokens_to_railway():
    """Gửi token mới lên Railway server (nếu đang chạy local)."""
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID")
    if is_railway:
        return  # Đang chạy trên Railway rồi, không cần sync

    try:
        async with httpx.AsyncClient(timeout=10.0) as sync_client:
            resp = await sync_client.post(
                "https://chathay-production.up.railway.app/api/update-tokens",
                json={
                    "secret": ZALO_APP_SECRET,
                    "access_token": ZALO_OA_ACCESS_TOKEN,
                    "refresh_token": ZALO_REFRESH_TOKEN,
                },
            )
            if resp.status_code == 200:
                logger.info("✅ Auto-synced new tokens to Railway!")
            else:
                logger.warning("Railway sync returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("Failed to auto-sync tokens to Railway: %s", e)


async def _refresh_zalo_token() -> bool:
    """Refresh Zalo OAuth token. Thread-safe, chống double-refresh."""
    global ZALO_OA_ACCESS_TOKEN, ZALO_REFRESH_TOKEN, _last_successful_refresh_time

    async with _token_lock:
        # ── Guard: nếu vừa refresh xong (< 5s trước), skip ──
        # Giải quyết race condition: 2 request cùng thấy -216, nhưng
        # request thứ 2 không nên gọi lại vì request 1 đã refresh rồi.
        elapsed = time.time() - _last_successful_refresh_time
        if elapsed < _MIN_REFRESH_INTERVAL:
            logger.info("Token was just refreshed %.1fs ago — skipping duplicate refresh", elapsed)
            return True  # Token đã mới rồi, return True để retry với token mới

        if not ZALO_REFRESH_TOKEN or not ZALO_APP_ID or not ZALO_APP_SECRET:
            logger.error("Missing refresh_token, app_id, or app_secret to refresh token")
            return False

        current_refresh = ZALO_REFRESH_TOKEN  # Snapshot trước khi gọi API
        logger.info("Attempting to refresh Zalo token (refresh_token ends: ...%s)...",
                     current_refresh[-8:] if len(current_refresh) > 8 else "***")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    ZALO_OAUTH_URL,
                    headers={"secret_key": ZALO_APP_SECRET},
                    data={
                        "app_id": ZALO_APP_ID,
                        "grant_type": "refresh_token",
                        "refresh_token": current_refresh,
                    },
                )
            data = res.json()

            if "access_token" in data:
                new_access = data["access_token"]
                new_refresh = data.get("refresh_token", current_refresh)

                ZALO_OA_ACCESS_TOKEN = new_access
                ZALO_REFRESH_TOKEN = new_refresh
                _last_successful_refresh_time = time.time()

                # Lưu vào DB ngay lập tức
                save_tokens(new_access, new_refresh)
                logger.info("✅ Zalo token refreshed! New access ends: ...%s, new refresh ends: ...%s",
                            new_access[-8:], new_refresh[-8:] if len(new_refresh) > 8 else "***")

                # Sync lên Railway (nếu đang chạy local) — dùng client MỚI
                await _sync_tokens_to_railway()
                return True

            else:
                error_code = data.get("error", "unknown")
                error_name = data.get("error_name", "")
                logger.error("❌ Token refresh FAILED (error=%s, name=%s): %s",
                             error_code, error_name, data)

                # Nếu refresh token bị invalid (14014), log rõ ràng
                if error_code == -14014 or error_code == 14014 or "Invalid refresh token" in str(data):
                    logger.critical(
                        "🚨 REFRESH TOKEN ĐÃ HẾT HẠN! Cần lấy token mới từ Zalo Developer Portal.\n"
                        "   Bước 1: Vào https://developers.zalo.me → chọn app → lấy token mới\n"
                        "   Bước 2: Chạy cap_nhat_token_len_server.py hoặc POST /api/update-tokens"
                    )
                return False

        except Exception as e:
            logger.error("Error during token refresh: %s", e, exc_info=True)
            return False


async def _proactive_token_refresh_loop():
    """Background loop: tự refresh token mỗi 30 phút TRƯỚC KHI nó hết hạn.
    
    Zalo access_token sống ~1 giờ. Nếu chờ đến khi bị -216 mới refresh,
    user message sẽ bị delay hoặc mất. Proactive refresh = không bao giờ hết hạn.
    """
    logger.info("🔄 Proactive token refresh scheduler started (every %d min)",
                _PROACTIVE_REFRESH_INTERVAL // 60)
    
    # Chờ 60s sau khi server start trước khi bắt đầu (tránh refresh ngay lúc cold start)
    await asyncio.sleep(60)
    
    while True:
        try:
            logger.info("🔄 Proactive token refresh triggered...")
            success = await _refresh_zalo_token()
            if success:
                logger.info("🔄 Proactive refresh OK — next in %d min", _PROACTIVE_REFRESH_INTERVAL // 60)
            else:
                logger.warning("🔄 Proactive refresh FAILED — will retry in 5 min")
                await asyncio.sleep(5 * 60)  # Retry sớm hơn nếu fail
                continue
        except Exception as e:
            logger.error("Proactive refresh error: %s", e, exc_info=True)
        
        await asyncio.sleep(_PROACTIVE_REFRESH_INTERVAL)


# ═══════════════════════════════════════════════════════════════
# RATE LIMITING
# ═══════════════════════════════════════════════════════════════

def check_rate_limit(user_id: str) -> bool:
    today = time.strftime("%Y-%m-%d")
    if user_id not in user_daily_usage:
        user_daily_usage[user_id] = {"date": today, "count": 0}
    if user_daily_usage[user_id]["date"] != today:
        user_daily_usage[user_id] = {"date": today, "count": 0}
    return int(user_daily_usage[user_id]["count"]) < config.FREE_DAILY_LIMIT


def increment_usage(user_id: str):
    today = time.strftime("%Y-%m-%d")
    if user_id not in user_daily_usage or user_daily_usage[user_id]["date"] != today:
        user_daily_usage[user_id] = {"date": today, "count": 0}
    user_daily_usage[user_id]["count"] = int(user_daily_usage[user_id]["count"]) + 1


# ═══════════════════════════════════════════════════════════════
# TEXT UTILITIES
# ═══════════════════════════════════════════════════════════════

def clean_preview_text(text: str, max_len: int = 180) -> str:
    cleaned = " ".join(text.replace("\n", " ").split()).strip()
    cleaned = cleaned.lstrip("-*0123456789. )(").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def split_message_for_zalo(text: str, limit: int = ZALO_TEXT_LIMIT) -> list[str]:
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


# ═══════════════════════════════════════════════════════════════
# SUMMARY STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def remember_summary(user_id: str, title: str, structured_summary: dict[str, Any], image_url: str = ""):
    latest_summary_by_user[user_id] = {"title": title, "data": structured_summary, "image_url": image_url}


def get_latest_summary(user_id: str) -> dict[str, Any] | None:
    return latest_summary_by_user.get(user_id)


def get_point_from_command(text: str) -> int | None:
    normalized = text.strip().lower()
    normalized = normalized.replace("chi tiết", "chi tiet")
    for token in normalized.replace("nghe", " ").replace("chi tiet", " ").split():
        if token.isdigit():
            return int(token)
    if normalized.isdigit():
        return int(normalized)
    return None


def get_summary_points(structured_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return list(structured_summary.get("points", []))


# ═══════════════════════════════════════════════════════════════
# BUTTON BUILDERS
# ═══════════════════════════════════════════════════════════════

def build_point_buttons(points: list[dict[str, Any]], payload_prefix: str = "") -> list[dict[str, str]]:
    buttons: list[dict[str, str]] = []
    for point in points:
        payload = f"{payload_prefix}{point['index']}".strip()
        buttons.append({
            "title": f"📌 Ý {point['index']}",
            "type": "oa.query.show",
            "payload": payload,
        })
    return buttons


def build_summary_buttons(structured_summary: dict[str, Any]) -> list[dict[str, str]]:
    points = get_summary_points(structured_summary)
    primary_points = points[:ZALO_PRIMARY_POINT_BUTTONS]
    buttons = build_point_buttons(primary_points)
    if len(points) > ZALO_PRIMARY_POINT_BUTTONS and len(buttons) < ZALO_MAX_BUTTONS:
        buttons.append({
            "title": "📚 Ý còn lại",
            "type": "oa.query.show",
            "payload": ZALO_SHOW_MORE_PAYLOAD,
        })
    return buttons


def build_more_points_buttons(structured_summary: dict[str, Any]) -> list[dict[str, str]]:
    points = get_summary_points(structured_summary)[ZALO_PRIMARY_POINT_BUTTONS:]
    buttons = build_point_buttons(points[: ZALO_MAX_BUTTONS - 1])
    if len(buttons) < ZALO_MAX_BUTTONS:
        buttons.append({
            "title": "🔙 Tóm tắt",
            "type": "oa.query.show",
            "payload": ZALO_BACK_TO_SUMMARY_PAYLOAD,
        })
    return buttons


# ═══════════════════════════════════════════════════════════════
# MESSAGE FORMATTING
# ═══════════════════════════════════════════════════════════════

def format_summary_menu(
    title: str,
    structured_summary: dict[str, Any],
    elapsed_seconds: float | None = None,
) -> str:
    """Format bản tóm tắt chính với doc type label."""
    points = get_summary_points(structured_summary)
    lines: list[str] = []

    # Document type badge (NEW)
    doc_type = structured_summary.get("document_type", "")
    if doc_type:
        type_label = get_doc_type_label(doc_type)
        lines.append(f"{type_label}")
        lines.append("")

    lines.append(f"📖 Đọc xong! Tóm tắt '{title}':")
    if elapsed_seconds is not None:
        lines.append(f"⏱ Xử lý trong {elapsed_seconds:.0f} giây")
    lines.append("")

    overview = structured_summary.get("overview", "")
    if overview:
        lines.append(f"📌 Tổng quan: {overview}\n")

    lines.append(f"📋 {len(points)} ý nổi bật:")
    for point in points:
        lines.append(f"🔹 {point['index']}. {point['title']}: {clean_preview_text(point['brief'])}")

    lines.append("")
    if len(points) > ZALO_PRIMARY_POINT_BUTTONS:
        lines.append(
            f"👉 Bấm nút xem {ZALO_PRIMARY_POINT_BUTTONS} ý đầu. "
            f"Bấm 'Ý còn lại' hoặc nhắn số {ZALO_PRIMARY_POINT_BUTTONS + 1}-{len(points)} để xem tiếp."
        )
    else:
        lines.append("👉 Bấm vào ý muốn xem kỹ, hoặc nhắn 'NGHE 1', 'NGHE 2'... để nghe audio.")

    return "\n".join(lines)


def format_remaining_points_menu(structured_summary: dict[str, Any]) -> str:
    points = get_summary_points(structured_summary)[ZALO_PRIMARY_POINT_BUTTONS:]
    if not points:
        return "Tài liệu này không còn ý nào khác. Bạn có thể bấm vào các nút ở trên để xem chi tiết."

    lines = ["📚 Các ý còn lại cũng quan trọng:"]
    for point in points:
        lines.append(f"🔹 {point['index']}. {point['title']}: {clean_preview_text(point['brief'])}")
    lines.append("")
    lines.append("👉 Bấm nút bên dưới hoặc nhắn số tương ứng để xem chi tiết.")
    return "\n".join(lines)


def format_point_detail(structured_summary: dict[str, Any], point_index: int) -> str:
    point = structured_summary["points"][point_index - 1]
    return (
        f"📝 Ý {point_index}: {point['title']}\n\n"
        f"Chi tiết:\n{point['detail']}"
    )


def format_ocr_result(ocr_text: str) -> str:
    """Format kết quả trích xuất chữ từ ảnh."""
    msg = f"📋 Chữ trích xuất từ ảnh:\n\n{ocr_text}"

    # Cắt nếu quá dài cho Zalo
    if len(msg) > ZALO_TEXT_LIMIT:
        msg = msg[:ZALO_TEXT_LIMIT - 60] + "\n\n[...text quá dài, đã cắt bớt]"

    return msg


# ═══════════════════════════════════════════════════════════════
# USER-FACING MESSAGES (v2.0)
# ═══════════════════════════════════════════════════════════════

def get_welcome_message() -> str:
    """Welcome message v2.0."""
    return (
        "🌟 Chào mừng bạn đến với CHAT HAY — Trợ lý đọc tài liệu AI!\n\n"
        "Khác với AI chat thông thường, mình chuyên ĐỌC & TÓM TẮT "
        "tài liệu thành các ý chính dễ hiểu nhất.\n\n"
        "📎 Gửi cho mình:\n"
        "• PDF, Word (.docx) → tóm tắt chuyên sâu\n"
        "• Ảnh chụp tài liệu → phân tích AI + trích xuất chữ\n"
        "• Đoạn văn bản dài → rút gọn thành ý chính\n\n"
        "🚀 Mình làm được:\n"
        "• Tóm tắt thông minh (3-8 ý theo độ phức tạp)\n"
        "• Trích xuất chữ từ ảnh (bấm nút khi cần)\n"
        "• Phân loại tài liệu (hóa đơn, hợp đồng, giấy tờ…)\n"
        "• Đọc nội dung bằng giọng nói 🔊\n\n"
        "📩 Gửi file hoặc ảnh ngay để bắt đầu!"
    )


def get_upload_prompt() -> str:
    return (
        "📎 Gửi PDF, Word hoặc ảnh tài liệu nhé!\n"
        "Mình sẽ tóm tắt cho bạn ngay."
    )


def get_processing_message(kind: str = "tài liệu") -> str:
    return f"📖 Đang đọc {kind} của bạn...\n⏳ Chờ khoảng 15-30 giây nhé!"


def get_menu_message() -> str:
    """Menu tính năng."""
    return (
        "📖 CHAT HAY — Trợ lý đọc tài liệu AI\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📎 GỬI FILE → Tóm tắt PDF, Word chuyên sâu\n"
        "🖼️ GỬI ẢNH → Phân tích AI + trích xuất chữ (tùy chọn)\n"
        "✍️ GỬI VĂN BẢN DÀI → Rút gọn thành ý chính\n\n"
        "⌨️ Lệnh nhanh:\n"
        "• Nhắn số 1-8 → Xem chi tiết từng ý\n"
        "• NGHE 1, NGHE 2… → Nghe audio từng ý\n"
        "• TRICH XUAT → Trích xuất chữ từ ảnh vừa gửi\n"
        "• DEADLINE → Xem tất cả deadline sắp đến\n"
        "• XONG [keyword] → Đánh dấu deadline hoàn thành\n"
        "• MENU → Xem bảng này\n\n"
        "✨ Tại sao chọn CHAT HAY?\n"
        "• Phân tích nội dung tài liệu chuyên sâu\n"
        "• Phân loại tài liệu tự động (hóa đơn, hợp đồng…)\n"
        "• ⏰ Tự trích xuất deadline & nhắc nhở đúng hạn\n\n"
        f"📊 Miễn phí: {config.FREE_DAILY_LIMIT} lượt/ngày"
    )



# ═══════════════════════════════════════════════════════════════
# SIGNATURE VERIFICATION
# ═══════════════════════════════════════════════════════════════

def verify_zalo_signature(request_body: bytes, mac_header: str) -> bool:
    if not ZALO_OA_SECRET or not mac_header:
        return True
    expected = hmac.new(
        ZALO_OA_SECRET.encode("utf-8"),
        request_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, mac_header)


# ═══════════════════════════════════════════════════════════════
# ZALO API CALLS
# ═══════════════════════════════════════════════════════════════

async def send_text_message(user_id: str, text: str, is_retry: bool = False):
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
        if result.get("error") == -216 and not is_retry:
            logger.warning("Token expired (-216). Attempting auto-refresh...")
            if await _refresh_zalo_token():
                return await send_text_message(user_id, text, is_retry=True)
        logger.error("Zalo send failed: %s", result)
    return result


async def send_text_with_buttons(user_id: str, text: str, buttons: list[dict], is_retry: bool = False):
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{ZALO_API_URL}/message/cs",
            headers={
                "Content-Type": "application/json",
                "access_token": ZALO_OA_ACCESS_TOKEN,
            },
            json={
                "recipient": {"user_id": user_id},
                "message": {
                    "text": text,
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "buttons": buttons
                        }
                    }
                },
            },
        )

    result = response.json()
    if result.get("error") != 0:
        if result.get("error") == -216 and not is_retry:
            logger.warning("Token expired (-216). Attempting auto-refresh...")
            if await _refresh_zalo_token():
                return await send_text_with_buttons(user_id, text, buttons, is_retry=True)
        logger.error("Zalo send buttons failed: %s", result)
    return result


async def send_long_text_message(user_id: str, text: str, buttons: list[dict] | None = None):
    chunks = split_message_for_zalo(text)
    for i, chunk in enumerate(chunks):
        if i == len(chunks) - 1 and buttons:
            await send_text_with_buttons(user_id, chunk, buttons)
        else:
            await send_text_message(user_id, chunk)


async def send_summary_with_interactive_buttons(
    user_id: str,
    title: str,
    structured_summary: dict[str, Any],
    elapsed_seconds: float | None = None,
):
    text = format_summary_menu(title, structured_summary, elapsed_seconds)
    buttons = build_summary_buttons(structured_summary)
    await send_long_text_message(user_id, text, buttons)


async def send_remaining_points_menu(user_id: str, structured_summary: dict[str, Any]):
    text = format_remaining_points_menu(structured_summary)
    buttons = build_more_points_buttons(structured_summary)
    await send_long_text_message(user_id, text, buttons)


# ═══════════════════════════════════════════════════════════════
# FILE DOWNLOAD
# ═══════════════════════════════════════════════════════════════

async def download_zalo_file(file_url: str, save_path: str) -> bool:
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


# ═══════════════════════════════════════════════════════════════
# AUDIO HANDLING
# ═══════════════════════════════════════════════════════════════

async def send_audio_for_point(user_id: str, point_index: int):
    latest = get_latest_summary(user_id)
    if not latest:
        await send_text_message(user_id, "Chưa có bản tóm tắt nào gần đây. Gửi tài liệu trước nhé!")
        return
    if not config.FPT_AI_API_KEY:
        await send_text_message(user_id, "Tính năng đọc audio chưa được bật trên hệ thống này.")
        return

    points = latest["data"]["points"]
    if not 1 <= point_index <= len(points):
        await send_text_message(user_id, f"Chỉ số không hợp lệ. Hãy chọn từ 1 đến {len(points)}.")
        return

    point = points[point_index - 1]
    await send_text_message(user_id, f"🔊 Đang tạo audio cho ý {point_index}: {point['title']}...")
    audio_path = await text_to_speech(point["detail"])
    if not audio_path:
        await send_text_message(user_id, "Không tạo được audio lúc này. Bạn thử lại sau nhé!")
        return

    audio_filename = os.path.basename(audio_path)
    audio_url = f"https://chathay-production.up.railway.app/audio/{audio_filename}"
    await send_text_message(user_id, f"🎧 Nghe ý {point_index} tại đây:\n{audio_url}")
    asyncio.create_task(_cleanup_audio_later(audio_path))


async def _cleanup_audio_later(audio_path: str, delay_seconds: int = 3600):
    await asyncio.sleep(delay_seconds)
    await cleanup_audio(audio_path)


# ═══════════════════════════════════════════════════════════════
# INTERACTIVE COMMAND HANDLER
# ═══════════════════════════════════════════════════════════════

async def handle_interactive_command(user_id: str, text: str) -> bool:
    """Xử lý lệnh tương tác. Return True nếu đã xử lý."""
    normalized = text.strip().lower()
    latest = get_latest_summary(user_id)

    # ── MENU / HELP ──
    if normalized in {"menu", "help", "trợ giúp", "hướng dẫn", "huong dan"}:
        await send_text_message(user_id, get_menu_message())
        return True

    # ── TRÍCH XUẤT CHỮ (opt-in, tiết kiệm token) ──
    if normalized in {"trich xuat", "trích xuất", "trích xuất chữ", "trich xuat chu", "lay chu", "lấy chữ"}:
        await handle_ocr_request(user_id)
        return True

    # ── XEM THÊM / Ý CÒN LẠI ──
    if normalized in {ZALO_SHOW_MORE_PAYLOAD.lower(), "xem thêm", "y con lai", "ý còn lại"}:
        if latest:
            await send_remaining_points_menu(user_id, latest["data"])
            return True

    # ── QUAY LẠI TÓM TẮT ──
    if normalized in {ZALO_BACK_TO_SUMMARY_PAYLOAD.lower(), "xem tóm tắt", "xem tom tat"}:
        if latest:
            await send_summary_with_interactive_buttons(user_id, latest["title"], latest["data"])
            return True

    # ── NGHE AUDIO ──
    if normalized.startswith("nghe"):
        point_index = get_point_from_command(normalized)
        if point_index is None:
            max_points = len(latest["data"]["points"]) if latest else ZALO_PRIMARY_POINT_BUTTONS
            await send_text_message(user_id, f"Hãy nhắn theo mẫu: NGHE 1, NGHE 2, ..., NGHE {max_points}")
            return True
        await send_audio_for_point(user_id, point_index)
        return True

    # ── XEM CHI TIẾT BẰNG SỐ ──
    if latest and normalized.isdigit():
        point_index = int(normalized)
        if 1 <= point_index <= len(latest["data"]["points"]):
            detail_text = format_point_detail(latest["data"], point_index)
            detail_buttons = [
                {
                    "title": f"🔊 Nghe đọc Ý {point_index}",
                    "type": "oa.query.show",
                    "payload": f"NGHE {point_index}"
                }
            ]
            await send_long_text_message(user_id, detail_text, detail_buttons)
            return True

    # ── CHI TIẾT + SỐ ──
    if latest and normalized.replace("chi tiết", "chi tiet").startswith("chi tiet"):
        point_index = get_point_from_command(normalized)
        if point_index is not None and 1 <= point_index <= len(latest["data"]["points"]):
            detail_text = format_point_detail(latest["data"], point_index)
            detail_buttons = [
                {
                    "title": f"🔊 Nghe đọc Ý {point_index}",
                    "type": "oa.query.show",
                    "payload": f"NGHE {point_index}"
                }
            ]
            await send_long_text_message(user_id, detail_text, detail_buttons)
            return True

    # ── MẬT KHẨU [keyword] — Vault retrieval ──
    if normalized.startswith(("mật khẩu", "mat khau", "password", "tk ", "tài khoản")):
        keyword = normalized
        for prefix in ["mật khẩu", "mat khau", "password", "tk", "tài khoản"]:
            keyword = keyword.replace(prefix, "").strip()
        if keyword:
            cred = get_vault_credential(user_id, keyword)
            if cred:
                msg = (
                    f"🔐 Thông tin đăng nhập **{cred['app_name']}**:\n\n"
                    f"• Trang: {cred.get('url', 'không rõ')}\n"
                    f"• Tài khoản: {cred['username']}\n"
                    f"• Mật khẩu: {cred['password']}\n\n"
                    f"Lưu trữ ngày {cred.get('saved_at', '')}. Chỉ bạn nhìn thấy tin nhắn này."
                )
                await send_text_message(user_id, msg)
                return True
            else:
                # Liệt kê những gì đang lưu
                all_creds = list_vault_credentials(user_id)
                if all_creds:
                    names = ", ".join(c["app_name"] for c in all_creds)
                    await send_text_message(
                        user_id,
                        f"Không tìm thấy '{keyword}'. Bạn đang lưu: {names}.\n"
                        "Nhắn 'mật khẩu [tên]' để xem."
                    )
                else:
                    await send_text_message(user_id, "Bạn chưa lưu mật khẩu nào. Gửi ảnh chụp màn hình có tài khoản để mình lưu giúp nhé!")
                return True

    # ── DANH SÁCH MẬT KHẨU ──
    if normalized in {"vault", "kho mat khau", "kho mật khẩu", "ds mat khau", "ds mật khẩu"}:
        all_creds = list_vault_credentials(user_id)
        if all_creds:
            lines = ["🔐 Kho mật khẩu của bạn:"]
            for c in all_creds:
                lines.append(f"  • {c['app_name']} ({c['username']}) — lưu {c['saved_at']}")
            lines.append("\nNhắn 'mật khẩu [tên]' để xem chi tiết.")
            await send_text_message(user_id, "\n".join(lines))
        else:
            await send_text_message(user_id, "Bạn chưa lưu mật khẩu nào. Gửi ảnh chụp màn hình có tài khoản để mình lưu giúp nhé!")
        return True

    # ── DEADLINE / LỊCH — Xem tất cả deadline ──
    if normalized in {"deadline", "deadlines", "lich", "lịch", "han", "hạn", "nhac nho", "nhắc nhở", "xem deadline"}:
        deadlines = get_user_deadlines(user_id)
        msg = format_deadline_list(deadlines)
        await send_text_message(user_id, msg)
        return True

    # ── XONG [keyword] — Đánh dấu deadline hoàn thành ──
    if normalized.startswith(("xong ", "done ", "hoan thanh ", "hoàn thành ")):
        keyword = normalized
        for prefix in ["xong", "done", "hoan thanh", "hoàn thành"]:
            keyword = keyword.replace(prefix, "").strip()
        if keyword:
            if mark_deadline_done(user_id, keyword):
                await send_text_message(user_id, f"✅ Đã đánh dấu hoàn thành deadline liên quan đến '{keyword}'!")
            else:
                await send_text_message(
                    user_id,
                    f"Không tìm thấy deadline nào liên quan đến '{keyword}'.\n"
                    "Nhắn 'DEADLINE' để xem danh sách."
                )
            return True

    return False


async def handle_ocr_request(user_id: str):
    """Xử lý yêu cầu trích xuất chữ — chỉ chạy khi user bấm nút."""
    image_url = last_image_url_by_user.get(user_id)
    if not image_url:
        await send_text_message(user_id, "Chưa có ảnh nào gần đây. Gửi ảnh trước rồi bấm 'Trích xuất chữ' nhé!")
        return

    await send_text_message(user_id, "📋 Đang trích xuất chữ từ ảnh...\n⏳ Chờ khoảng 10-15 giây nhé!")

    image_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_ocr.jpg")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                await send_text_message(user_id, "Không tải được ảnh. Gửi lại ảnh mới nhé!")
                return
            with open(image_path, "wb") as f:
                f.write(response.content)

        ocr_text = await extract_ocr_text(image_path)
        result_msg = format_ocr_result(ocr_text)
        await send_text_message(user_id, result_msg)
    except Exception as exc:
        logger.error("OCR request failed: %s", exc, exc_info=True)
        await send_text_message(user_id, "Không trích xuất được chữ lúc này. Thử lại sau nhé!")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


# ═══════════════════════════════════════════════════════════════
# FASTAPI APP SETUP
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("CHAT HAY v3.0 — Zalo OA Webhook Server starting...")
    logger.info("OA Token set: %s", "YES" if ZALO_OA_ACCESS_TOKEN else "NO")
    logger.info("OA Secret set: %s", "YES" if ZALO_OA_SECRET else "NO")
    logger.info("App ID: %s", ZALO_APP_ID)
    logger.info("Features: OCR ✓ | Doc Classification ✓ | TTS ✓ | Deadline Reminder ✓ | Proactive Token Refresh ✓")
    logger.info("=" * 60)

    # Inject message sender vào deadline service (tránh circular import)
    set_message_sender(send_text_message)

    # Khởi động background schedulers
    scheduler_task = asyncio.create_task(start_reminder_scheduler())
    token_refresh_task = asyncio.create_task(_proactive_token_refresh_loop())

    yield

    # Cleanup
    stop_reminder_scheduler()
    scheduler_task.cancel()
    token_refresh_task.cancel()
    logger.info("Server shutting down...")


app = FastAPI(title="CHAT HAY v2.0 — Trợ lý đọc tài liệu AI", lifespan=lifespan)
app.mount("/audio", StaticFiles(directory=config.AUDIO_DIR), name="audio")

HOMEPAGE_HTML = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta name="zalo-platform-site-verification" content="{ZALO_VERIFICATION_CODE}" />
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CHAT HAY — Trợ lý đọc tài liệu AI</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #0a0e1a; color: #f0f0f5; display: flex; justify-content: center; padding: 40px; }}
.container {{ max-width: 600px; text-align: center; }}
h1 {{ background: linear-gradient(135deg, #6c5ce7, #00cec9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2em; }}
.badge {{ display: inline-block; background: #1a2035; border: 1px solid #2d3555; border-radius: 8px; padding: 4px 12px; margin: 4px; font-size: 13px; }}
.status {{ color: #00cec9; }}
</style>
</head>
<body>
<div class="container">
<h1>📖 CHAT HAY v2.0</h1>
<p>Trợ lý đọc tài liệu AI trên Zalo</p>
<p class="status">● Server đang hoạt động</p>
<div>
<span class="badge">📄 PDF/Word</span>
<span class="badge">🖼️ OCR ảnh</span>
<span class="badge">🔊 Audio TTS</span>
<span class="badge">🏷️ Phân loại tài liệu</span>
</div>
<p style="margin-top:20px;color:#8892b0;font-size:13px;">
App ID: {ZALO_APP_ID}<br>
Webhook: POST /webhook/zalo
</p>
</div>
</body>
</html>"""

VERIFIER_HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta name="zalo-platform-site-verification" content="{ZALO_VERIFICATION_CODE}" />
</head>
<body>{ZALO_VERIFICATION_CODE}</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# HTTP ROUTES
# ═══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def health():
    return HTMLResponse(content=HOMEPAGE_HTML, status_code=200)


@app.get(f"/zalo_verifier{ZALO_VERIFICATION_CODE}.html", response_class=HTMLResponse)
async def zalo_verifier():
    return HTMLResponse(content=VERIFIER_HTML, status_code=200)


@app.get("/webhook/zalo")
async def webhook_verify():
    return JSONResponse(content={"status": "ok", "message": "CHAT HAY v2.0 webhook active"}, status_code=200)


@app.get("/debug/tokens")
async def debug_tokens():
    """Endpoint debug: xem trạng thái token hiện tại."""
    info = get_token_info()
    info["memory_access_token_len"] = len(ZALO_OA_ACCESS_TOKEN)
    info["memory_refresh_token_len"] = len(ZALO_REFRESH_TOKEN)
    info["version"] = "2.0"
    info["features"] = ["ocr", "doc_classification", "tts"]
    return JSONResponse(content=info, status_code=200)


@app.post("/api/update-tokens")
async def api_update_tokens(request: Request):
    """Endpoint cập nhật token từ xa (từ local hoặc deploy script)."""
    global ZALO_OA_ACCESS_TOKEN, ZALO_REFRESH_TOKEN, _last_successful_refresh_time
    try:
        body = await request.json()
        secret = body.get("secret", "")
        if secret != ZALO_APP_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret")

        new_access = body.get("access_token", "")
        new_refresh = body.get("refresh_token", "")
        if not new_access or not new_refresh:
            return JSONResponse(content={"error": "Missing access_token or refresh_token"}, status_code=400)

        ZALO_OA_ACCESS_TOKEN = new_access
        ZALO_REFRESH_TOKEN = new_refresh
        _last_successful_refresh_time = time.time()  # Reset timer để tránh proactive refresh trùng
        save_tokens(new_access, new_refresh)

        logger.info("✅ Tokens updated via /api/update-tokens (access ends: ...%s)", new_access[-8:])
        return JSONResponse(content={"status": "ok", "message": "Tokens updated successfully"}, status_code=200)
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=500)


# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS (Web Upload / Windows Send-To)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/summarize")
async def api_summarize(file: UploadFile = File(...)):
    """API endpoint cho Web Upload Portal. Nhận file, trả JSON tóm tắt."""
    try:
        file_name = file.filename or "document"
        file_type = get_file_type(file_name)

        if file_type == "unknown":
            return JSONResponse(content={"error": "Chỉ hỗ trợ PDF, Word (.docx), hoặc ảnh."}, status_code=400)

        # Save temp file
        file_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_{file_name}")
        content = await file.read()

        if len(content) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            return JSONResponse(content={"error": f"File quá lớn! Tối đa {config.MAX_FILE_SIZE_MB}MB."}, status_code=400)

        with open(file_path, "wb") as f:
            f.write(content)

        try:
            if file_type == "image":
                structured = await summarize_image_structured(file_path)
            else:
                text, _ft = await extract_text(file_path, config.MAX_PAGES)
                if not text:
                    return JSONResponse(content={"error": "Không đọc được nội dung file này."}, status_code=400)
                structured = await summarize_text_structured(text)

            if structured.get("error"):
                return JSONResponse(content={"error": str(structured["error"])}, status_code=500)

            return JSONResponse(content=structured, status_code=200)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as exc:
        logger.error("API summarize error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": "Đã xảy ra lỗi. Vui lòng thử lại!"}, status_code=500)


@app.post("/api/summarize-view", response_class=HTMLResponse)
async def api_summarize_view(file: UploadFile = File(...)):
    """Upload file → trả về trang HTML kết quả đẹp (cho Send To trên Windows)."""
    try:
        file_name = file.filename or "document"
        file_type = get_file_type(file_name)

        if file_type == "unknown":
            return HTMLResponse(content="<h1>Chỉ hỗ trợ PDF, Word, hoặc ảnh.</h1>", status_code=400)

        file_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_{file_name}")
        content = await file.read()

        if len(content) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            return HTMLResponse(content=f"<h1>File quá lớn! Tối đa {config.MAX_FILE_SIZE_MB}MB.</h1>", status_code=400)

        with open(file_path, "wb") as f:
            f.write(content)

        try:
            if file_type == "image":
                structured = await summarize_image_structured(file_path)
            else:
                text, _ft = await extract_text(file_path, config.MAX_PAGES)
                if not text:
                    return HTMLResponse(content="<h1>Không đọc được nội dung file này.</h1>", status_code=400)
                structured = await summarize_text_structured(text)

            if structured.get("error"):
                return HTMLResponse(content=f"<h1>{structured['error']}</h1>", status_code=500)

            # Build beautiful HTML result page
            title = structured.get("document_title", "Tài liệu")
            overview = structured.get("overview", "")
            doc_type = structured.get("document_type", "")
            ocr_text = structured.get("ocr_text", "")

            # Document type badge
            type_badge = ""
            if doc_type:
                type_label = get_doc_type_label(doc_type)
                type_badge = f'<div class="type-badge">{type_label}</div>'

            # OCR section
            ocr_section = ""
            if ocr_text and len(ocr_text.strip()) > 5:
                escaped_ocr = ocr_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                ocr_section = f'''<div class="ocr-section">
                    <div class="ocr-header" onclick="this.parentElement.classList.toggle('open')">
                        📋 Text trích xuất từ ảnh (OCR) <span class="ocr-toggle">▼</span>
                    </div>
                    <pre class="ocr-text">{escaped_ocr}</pre>
                </div>'''

            points_html = ""
            for p in structured.get("points", []):
                points_html += f"""<div class="c" onclick="this.classList.toggle('o')">
                    <div class="h"><div class="n">{p['index']}</div><div class="tt">{p['title']}</div><div class="tg">▼</div></div>
                    <div class="b">{p['brief']}</div>
                    <div class="d">{p['detail']}</div></div>"""

            html = f"""<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Read AI — {title}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Inter',sans-serif;background:#0a0e1a;color:#f0f0f5;padding:40px 20px}}
body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 20% 50%,rgba(108,92,231,.12) 0%,transparent 50%),radial-gradient(ellipse at 80% 20%,rgba(0,206,201,.08) 0%,transparent 50%);pointer-events:none}}
.w{{max-width:700px;margin:0 auto;position:relative;z-index:1}}.logo{{text-align:center;font-size:32px;font-weight:800;background:linear-gradient(135deg,#6c5ce7,#00cec9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px}}
.sub{{text-align:center;color:#8892b0;font-size:13px;margin-bottom:28px}}.hdr{{background:linear-gradient(135deg,#131829,#1a2035);border:1px solid #2d3555;border-radius:16px;padding:24px;margin-bottom:16px}}
.dt{{font-size:20px;font-weight:700;margin-bottom:8px}}.ov{{color:#8892b0;font-size:14px;line-height:1.6;padding-left:12px;border-left:3px solid #6c5ce7}}
.type-badge{{display:inline-block;background:#1a2035;border:1px solid #6c5ce7;border-radius:20px;padding:4px 14px;font-size:13px;margin-bottom:12px}}
.c{{background:#131829;border:1px solid #2d3555;border-radius:14px;margin-bottom:10px;cursor:pointer;overflow:hidden;transition:all .3s}}.c:hover{{border-color:#6c5ce7;transform:translateX(4px)}}
.h{{display:flex;align-items:center;gap:12px;padding:16px 20px}}.n{{width:32px;height:32px;background:linear-gradient(135deg,#6c5ce7,#a29bfe);border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0}}
.tt{{font-weight:600;font-size:15px;flex:1}}.tg{{color:#8892b0;transition:transform .3s;font-size:16px}}.c.o .tg{{transform:rotate(180deg)}}
.b{{padding:0 20px 12px;font-size:13px;color:#8892b0}}.d{{display:none;padding:16px 20px;font-size:14px;line-height:1.7;border-top:1px solid #2d3555}}
.c.o .d{{display:block}}
.ocr-section{{background:#131829;border:1px solid #2d3555;border-radius:14px;margin-bottom:16px;overflow:hidden}}
.ocr-header{{padding:16px 20px;cursor:pointer;font-weight:600;display:flex;justify-content:space-between;align-items:center}}
.ocr-header:hover{{background:#1a2035}}.ocr-toggle{{color:#8892b0;transition:transform .3s}}
.ocr-section.open .ocr-toggle{{transform:rotate(180deg)}}
.ocr-text{{display:none;padding:16px 20px;font-size:13px;line-height:1.6;border-top:1px solid #2d3555;white-space:pre-wrap;word-break:break-word;font-family:'Courier New',monospace;color:#a0aec0;max-height:400px;overflow-y:auto}}
.ocr-section.open .ocr-text{{display:block}}
.fb{{text-align:center;color:#8892b0;font-size:12px;margin-top:20px}}</style></head>
<body><div class="w"><div class="logo">📖 CHAT HAY v2.0</div><div class="sub">Trợ lý đọc tài liệu AI</div>
<div class="hdr">{type_badge}<div class="dt">📖 {title}</div><div class="ov">{overview}</div></div>
{ocr_section}
{points_html}<div class="fb">📄 File: {file_name}</div></div></body></html>"""
            return HTMLResponse(content=html, status_code=200)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as exc:
        logger.error("API summarize-view error: %s", exc, exc_info=True)
        return HTMLResponse(content="<h1>Đã xảy ra lỗi. Vui lòng thử lại!</h1>", status_code=500)


# ═══════════════════════════════════════════════════════════════
# WEBHOOK EVENT PROCESSING
# ═══════════════════════════════════════════════════════════════

async def process_webhook_event(body: dict):
    try:
        event_name = body.get("event_name", "")
        sender_id = body.get("sender", {}).get("id", "")
        logger.info("Processing event: %s from %s", event_name, sender_id)

        # ── HỆ THỐNG CHỐNG SPAM (COOLDOWN) ──
        if sender_id and event_name in {"user_send_text", "user_send_image", "user_send_file"}:
            now = time.time()
            last_time = user_cooldowns.get(sender_id, 0)
            if now - last_time < COOLDOWN_SECONDS:
                last_warn = user_warnings.get(sender_id, 0)
                if now - last_warn > 60:  # Chỉ báo nhắc nhở 1 lần mỗi phút để tránh Zalo rate limit
                    user_warnings[sender_id] = now
                    # Fire & forget warning message
                    asyncio.create_task(send_text_message(
                        sender_id,
                        f"☕ Từ từ nhé bạn ơi! Mình cần chút thời gian để xử lý mỗi yêu cầu thật chu đáo.\n\n"
                        f"Gửi lại sau {COOLDOWN_SECONDS} giây là mình sẵn sàng phục vụ ngay thôi ạ! 😊"
                    ))
                logger.warning(f"SPAM BLOCKED: User {sender_id} sent message within cooldown.")
                return  # Skip processing this event silently to save server loads
            user_cooldowns[sender_id] = now

        # Ghi nhận tương tác → refresh cửa sổ 7 ngày cho deadline reminder
        if sender_id:
            update_user_interaction(sender_id)

        if event_name == "follow":
            await send_text_message(sender_id, get_welcome_message())
            return

        if event_name == "user_send_text":
            # Gửi nhắc nhở deadline tích lũy khi user quay lại
            await _send_pending_deadline_notifications(sender_id)
            await handle_zalo_text(sender_id, body.get("message", {}).get("text", ""))
            return

        if event_name == "user_send_image":
            await _send_pending_deadline_notifications(sender_id)
            attachments = body.get("message", {}).get("attachments", [])
            if attachments:
                await handle_zalo_image(sender_id, attachments[0].get("payload", {}).get("url", ""))
            return

        if event_name == "user_send_file":
            await _send_pending_deadline_notifications(sender_id)
            attachments = body.get("message", {}).get("attachments", [])
            if attachments:
                payload = attachments[0].get("payload", {})
                await handle_zalo_file(
                    sender_id,
                    payload.get("url", ""),
                    payload.get("name", "document"),
                    payload.get("size", 0),
                )
            return

        logger.info("Unhandled event: %s", event_name)
    except Exception as exc:
        logger.error("Error processing event: %s", exc, exc_info=True)


async def _send_pending_deadline_notifications(user_id: str):
    """Gửi nhắc nhở deadline tích lũy khi user quay lại tương tác."""
    try:
        pending = get_pending_notifications(user_id)
        if not pending:
            return

        from services.deadline_service import format_reminder_message, mark_reminder_sent
        for dl in pending[:3]:  # Tối đa 3 nhắc nhở cùng lúc
            msg = format_reminder_message(dl, "today")
            await send_text_message(user_id, msg)
            mark_reminder_sent(user_id, dl, "today")
            await asyncio.sleep(0.5)
    except Exception as exc:
        logger.error("Pending deadline notification error: %s", exc)


@app.post("/webhook/zalo")
async def zalo_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        raw_body = await request.body()
        mac_header = request.headers.get("mac", "")
        if ZALO_OA_SECRET and mac_header and not verify_zalo_signature(raw_body, mac_header):
            raise HTTPException(status_code=403, detail="Invalid signature")

        body = json.loads(raw_body)
        logger.info("Webhook received: %s from %s", body.get("event_name", ""), body.get("sender", {}).get("id", "unknown"))
        background_tasks.add_task(process_webhook_event, body)
        return JSONResponse(content={"status": "ok"}, status_code=200)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Webhook error: %s", exc, exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=200)


# ═══════════════════════════════════════════════════════════════
# MESSAGE HANDLERS
# ═══════════════════════════════════════════════════════════════

async def handle_zalo_text(user_id: str, text: str):
    """Xử lý text nhận từ user — smart flow với pending actions."""
    normalized = text.strip().lower()

    # ── PENDING ACTION: Bot đang chờ user trả lời gì đó (Silent Mode) ──
    pending = get_pending_action(user_id)
    if pending:
        action = pending["action"]
        data = pending["data"]

        # User xác nhận lưu mật khẩu
        if action == "confirm_save_vault":
            if normalized in {"lưu", "luu", "có", "co", "save", "lưu lại", "luu lai"}:
                save_vault_credential(
                    user_id,
                    data.get("app_name", "Không rõ"),
                    data.get("url", ""),
                    data.get("username", ""),
                    data.get("password", ""),
                )
                clear_pending_action(user_id)
                app_name = data.get("app_name", "hệ thống")
                await send_text_message(
                    user_id,
                    f"✅ Đã lưu mã hóa thành công!\n"
                    f"Lần sau nhắn 'mật khẩu {app_name}' để xem lại nhé. "
                    f"Chỉ bạn mới thấy được."
                )
                return
            elif normalized in {"không", "khong", "không cần", "khong can", "thôi", "thoi", "no"}:
                clear_pending_action(user_id)
                return

        # Hidden Feature: User nhắn tìm tên/tài khoản
        if action in {"ask_name_for_task", "ask_name_for_account"}:
            # Chỉ kích hoạt nếu user gõ có vẻ đang tìm kiếm (có keyword) hoặc text ngắn (chỉ gõ tên)
            is_search = any(kw in normalized for kw in ["tìm", "tim", "tên", "ten", "tài khoản", "tai khoan", "việc", "viec"])
            is_short_name = len(normalized.split()) <= 4
            
            if is_search or is_short_name:
                user_name = text.replace("tìm", "").replace("tên", "").replace("tài khoản", "").replace("của", "").strip()
                if not user_name:
                    user_name = text.strip()
                    
                clear_pending_action(user_id)
                doc_text = data.get("text", "")
                file_name = data.get("file_name", "tài liệu")

                if action == "ask_name_for_task":
                    await send_text_message(user_id, f"🔍 Đang rà soát việc được giao cho '{user_name}'...")
                    prompt = (
                        f"Tài liệu sau là quyết định phân công nhiệm vụ.\n"
                        f"Hãy tìm TẤT CẢ nhiệm vụ được giao cho người tên '{user_name}'.\n"
                        f"Với mỗi nhiệm vụ, nêu rõ: nội dung việc, deadline (nếu có).\n"
                        f"Nếu không thấy, trả lời 'Không tìm thấy thông tin của {user_name}'.\n\n"
                        f"NỘI DUNG TÀI LIỆU:\n{doc_text[:8000]}"
                    )
                else:
                    await send_text_message(user_id, f"🔍 Đang trích xuất tài khoản của '{user_name}'...")
                    prompt = (
                        f"Tài liệu sau là danh sách thông tin đăng nhập.\n"
                        f"Hãy tìm chính xác tài khoản, mật khẩu, và tên hệ thống của người tên '{user_name}'.\n"
                        f"Định dạng: Hệ thống: ... | Tài khoản: ... | Mật khẩu: ...\n"
                        f"Nếu không thấy, báo 'Không tìm thấy {user_name}'. Trả lời ngắn gọn ngập tức.\n\n"
                        f"NỘI DUNG TÀI LIỆU:\n{doc_text[:8000]}"
                    )

                result = await summarize_text_structured(prompt)
                if result.get("error"):
                    await send_text_message(user_id, str(result["error"]))
                else:
                    points = result.get("points", [])
                    if points:
                        await send_text_message(user_id, f"💡 Kết quả cho '{user_name}':\n\n{points[0].get('detail', '')}")
                    else:
                        await send_text_message(user_id, result.get("overview", "Không tìm thấy thông tin."))
                return

    # Lệnh tương tác (menu, số, nghe, chi tiết, vault...)
    if await handle_interactive_command(user_id, normalized):
        return

    # ── SMART REDIRECT: Hướng dẫn mềm mại khi user nhắn linh tinh ──
    # Không chặn thô thiển, mà dẫn dắt user hiểu cách dùng
    _useless_exact = {"chào", "hello", "hi", "hey", "alo", "ok", "oke", "haha", "hehe", "gì", "sao", "ơi", "ê", "yo"}
    _useless_phrases = ["bạn là ai", "chatgpt", "chat gpt", "ai tạo ra", "tử vi", "xem bói", "bạn là gì", "mày là ai", "bot à", "có phải ai", "giống chatgpt"]
    is_exact_useless = normalized in _useless_exact
    is_phrase_useless = any(kw in normalized for kw in _useless_phrases) and len(normalized) < 60
    if len(text.strip()) < 15 or is_exact_useless or is_phrase_useless:
        await send_text_message(
            user_id, 
            "👋 Chào bạn! Mình là CHAT HAY — chuyên gia đọc tài liệu bằng AI.\n\n"
            "💡 Mình có thể giúp bạn:\n"
            "  📎 Gửi file PDF/Word → Tóm tắt nhanh 5 ý chính\n"
            "  🖼️ Chụp ảnh hợp đồng/hóa đơn → Đọc và phân tích\n"
            "  ⏰ Phát hiện deadline → Tự nhắc nhở đúng hạn\n"
            "  🔒 Lưu mật khẩu → Kho bí mật an toàn\n\n"
            "Thử gửi 1 tấm ảnh hoặc file cho mình xem nhé! 😊"
        )
        return

    # Text dài → tóm tắt AI
    if not check_rate_limit(user_id):
        await send_text_message(
            user_id,
            f"Bạn đã dùng hết {config.FREE_DAILY_LIMIT} lượt miễn phí hôm nay. Quay lại ngày mai nhé!"
        )
        return

    await send_text_message(user_id, get_processing_message("nội dung"))
    structured = await summarize_text_structured(text)
    if structured.get("error"):
        await send_text_message(user_id, str(structured["error"]))
        return

    remember_summary(user_id, "văn bản bạn vừa gửi", structured)
    await send_summary_with_interactive_buttons(user_id, "văn bản bạn vừa gửi", structured)
    increment_usage(user_id)


async def handle_zalo_file(user_id: str, file_url: str, file_name: str, file_size):
    """Xử lý file PDF/Word từ user — smart flow: phát hiện phân công nhiệm vụ."""
    try:
        file_size = int(file_size)
    except (ValueError, TypeError):
        file_size = 0

    if not check_rate_limit(user_id):
        await send_text_message(
            user_id,
            f"Bạn đã dùng hết {config.FREE_DAILY_LIMIT} lượt miễn phí hôm nay."
        )
        return

    if file_size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
        await send_text_message(user_id, f"File quá lớn! Tối đa {config.MAX_FILE_SIZE_MB}MB.")
        return

    if get_file_type(file_name) == "unknown":
        await send_text_message(
            user_id,
            "Mình chỉ hỗ trợ file PDF, Word (.docx), hoặc ảnh. Vui lòng gửi đúng định dạng!"
        )
        return

    await send_text_message(user_id, get_processing_message("tài liệu"))
    start_time = time.time()
    file_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_{file_name}")

    try:
        if not await download_zalo_file(file_url, file_path):
            await send_text_message(user_id, "Không thể tải file. Vui lòng gửi lại!")
            return

        text, _file_type = await extract_text(file_path, config.MAX_PAGES)
        if not text:
            await send_text_message(
                user_id,
                "Không đọc được nội dung file này. Thử chụp ảnh tài liệu và gửi ảnh cho mình!"
            )
            return

        structured = await summarize_text_structured(text)
        if structured.get("error"):
            await send_text_message(user_id, str(structured["error"]))
            return

        doc_type = structured.get("document_type", "general")
        recommended_action = structured.get("recommended_action", "standard_summary")

        # ── SILENT STATE: AI nhận diện ý định tiềm ẩn ──
        if recommended_action == "ask_name_for_task":
            # Set action âm thầm, chờ user trigger bằng lệnh tìm kiếm
            set_pending_action(user_id, "ask_name_for_task", {
                "file_name": file_name,
                "text": text[:10000],
            })

        elif recommended_action == "ask_name_for_account":
            set_pending_action(user_id, "ask_name_for_account", {
                "file_name": file_name,
                "text": text[:10000],
            })

        # Xử lý tóm tắt bình thường, không nói hoạch toẹt ra là mình đang săm soi
        remember_summary(user_id, file_name, structured)
        await send_summary_with_interactive_buttons(user_id, file_name, structured, time.time() - start_time)
        increment_usage(user_id)

        # ── AUTO DEADLINE: Trích xuất và lưu deadlines ──
        deadline_count = save_deadlines_from_summary(user_id, structured, doc_title=file_name)
        if deadline_count > 0:
            notice = format_deadline_saved_notice(deadline_count, structured.get("deadlines", []))
            if notice:
                await send_text_message(user_id, notice)
    except Exception as exc:
        logger.error("File processing error: %s", exc, exc_info=True)
        await send_text_message(user_id, "Đã xảy ra lỗi. Vui lòng thử lại!")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def handle_zalo_image(user_id: str, image_url: str):
    """Xử lý ảnh từ user — smart flow: phát hiện mật khẩu, tóm tắt + nút trích xuất chữ."""
    if not check_rate_limit(user_id):
        await send_text_message(
            user_id,
            f"Bạn đã dùng hết {config.FREE_DAILY_LIMIT} lượt miễn phí hôm nay."
        )
        return

    # Lưu URL ảnh để trích xuất chữ sau khi user yêu cầu
    last_image_url_by_user[user_id] = image_url

    await send_text_message(user_id, get_processing_message("ảnh"))
    start_time = time.time()
    image_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}.jpg")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                await send_text_message(user_id, "Không tải được ảnh. Gửi lại nhé!")
                return
            with open(image_path, "wb") as image_file:
                image_file.write(response.content)

        # ── AI Summary (phân loại tài liệu + phát hiện mật khẩu) ──
        structured = await summarize_image_structured(image_path)
        if structured.get("error"):
            await send_text_message(user_id, str(structured["error"]))
            return

        doc_type = structured.get("document_type", "general")
        recommended_action = structured.get("recommended_action", "standard_summary")
        credentials = structured.get("credentials")

        # ═══ ẢNH THƯỜNG: Hướng dẫn nhẹ nhàng ═══
        if doc_type == "photo":
            await send_text_message(
                user_id, 
                "🖼️ Ảnh đẹp quá! Nhưng mình sẽ phát huy tốt hơn với tài liệu nhé 😊\n\n"
                "Hãy thử gửi cho mình:\n"
                "  📎 Hợp đồng, công văn, quyết định\n"
                "  🧳 Hóa đơn, biên lai\n"
                "  💊 Đơn thuốc, phiếu xét nghiệm\n"
                "  📝 Bảng điểm, thông báo trường học\n\n"
                "Mình sẽ tóm tắt, trích xuất deadline và nhắc nhở bạn đúng hạn!"
            )
            # Không cần refund vì increment_usage chưa được gọi ở thời điểm này
            return

        # ═══ NHÁNH Y TẾ: ĐƠN THUỐC — warning y tế ═══
        if doc_type == "medical" and recommended_action == "medical_warning":
            remember_summary(user_id, "ảnh bạn vừa gửi", structured, image_url=image_url)
            text_msg = format_summary_menu("ảnh bạn vừa gửi", structured, time.time() - start_time)
            text_msg += "\n\n⚠️ Lưu ý: Đây là giải thích AI, KHÔNG thay thế lời khuyên bác sĩ. Bạn hãy hỏi lại bác sĩ điều trị nếu có thắc mắc nhé!"
            buttons = build_summary_buttons(structured)
            if len(buttons) < ZALO_MAX_BUTTONS:
                buttons.append({
                    "title": "📋 Trích xuất chữ",
                    "type": "oa.query.show",
                    "payload": "TRICH XUAT",
                })
            await send_long_text_message(user_id, text_msg, buttons)
            increment_usage(user_id)

            # ── AUTO DEADLINE từ ảnh y tế ──
            dl_count = save_deadlines_from_summary(user_id, structured, doc_title="ảnh y tế")
            if dl_count > 0:
                notice = format_deadline_saved_notice(dl_count, structured.get("deadlines", []))
                if notice:
                    await send_text_message(user_id, notice)
            return

        # ═══ TÍNH NĂNG ẨN: PHÁT HIỆN MẬT KHẨU HOẶC DANH SÁCH ═══
        if recommended_action in {"ask_to_save_vault", "ask_name_for_account", "ask_name_for_task"}:
            
            # Ghi nhớ action nhưng im lặng
            if recommended_action == "ask_to_save_vault" and credentials:
                set_pending_action(user_id, "confirm_save_vault", {
                    "app_name": credentials.get("app_name", "hệ thống"),
                    "url": credentials.get("url", ""),
                    "username": credentials.get("username", ""),
                    "password": credentials.get("password", ""),
                })
            else:
                ocr_text = await extract_ocr_text(image_path)
                set_pending_action(user_id, recommended_action, {
                    "file_name": "ảnh chụp",
                    "text": ocr_text[:10000],
                })

            # Tóm tắt trả ra bình thường như không có gì xảy ra
            remember_summary(user_id, "ảnh bạn vừa gửi", structured, image_url=image_url)
            text_msg = format_summary_menu("ảnh bạn vừa gửi", structured, time.time() - start_time)
            buttons = build_summary_buttons(structured)
            if len(buttons) < ZALO_MAX_BUTTONS:
                buttons.append({
                    "title": "📋 Trích xuất chữ",
                    "type": "oa.query.show",
                    "payload": "TRICH XUAT",
                })
            await send_long_text_message(user_id, text_msg, buttons)
            increment_usage(user_id)

            # ── AUTO DEADLINE từ ảnh phát hiện ẩn ──
            dl_count = save_deadlines_from_summary(user_id, structured, doc_title="ảnh bạn vừa gửi")
            if dl_count > 0:
                notice = format_deadline_saved_notice(dl_count, structured.get("deadlines", []))
                if notice:
                    await send_text_message(user_id, notice)
            return

        # ═══ NHÁNH 3: MẶC ĐỊNH — Tóm tắt thông thường ═══
        remember_summary(user_id, "ảnh bạn vừa gửi", structured, image_url=image_url)

        text_msg = format_summary_menu("ảnh bạn vừa gửi", structured, time.time() - start_time)
        buttons = build_summary_buttons(structured)
        if len(buttons) < ZALO_MAX_BUTTONS:
            buttons.append({
                "title": "📋 Trích xuất chữ",
                "type": "oa.query.show",
                "payload": "TRICH XUAT",
            })
        await send_long_text_message(user_id, text_msg, buttons)

        increment_usage(user_id)

        # ── AUTO DEADLINE từ ảnh thường ──
        dl_count = save_deadlines_from_summary(user_id, structured, doc_title="ảnh bạn vừa gửi")
        if dl_count > 0:
            notice = format_deadline_saved_notice(dl_count, structured.get("deadlines", []))
            if notice:
                await send_text_message(user_id, notice)
    except Exception as exc:
        logger.error("Image processing error: %s", exc, exc_info=True)
        await send_text_message(user_id, "Không đọc được ảnh. Chụp rõ hơn và thử lại!")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(
        "zalo_webhook:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )
