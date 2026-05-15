"""Zalo OA webhook server — CHAT HAY v2.0

Core features:
  - Document summarization (PDF, Word, Image)
  - Q&A about documents
  - OCR text extraction
  - TTS audio reading
  - Document classification
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import random
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import httpx
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Import shared quiz router
try:
    from shared_quiz_api import router as shared_quiz_router
except ImportError:
    shared_quiz_router = None  # Will be handled later

from config import config
from services.ai_summarizer import (
    summarize_image_structured,
    summarize_text_structured,
    summarize_pdf_images_structured,
    extract_ocr_text,
    get_doc_type_label,
    answer_question_about_document,
    _call_with_smart_routing,
)
from services.document_parser import extract_text, get_file_type, convert_pdf_to_images
from services.tts_service import cleanup_audio, text_to_speech
from services.token_store import load_token, load_tokens, save_tokens, get_token_info
from services.db_service import (
    set_pending_action,
    get_pending_action,
    clear_pending_action,
    delete_user_data,
    delete_document_by_id,
    get_user_docs,
    get_supabase_client,
    supabase,
    check_rate_limit,
    increment_usage,
    get_document_by_id,
    save_document_content,
    get_active_doc,
    get_active_doc_id,
    save_document_text_temp,
    get_document_text_temp,
    renew_document_text_temp,
    get_qa_count,
    increment_qa_count,
    reset_qa_count,
    set_active_doc,
    load_study_session,
    save_study_session,
    clear_study_session,
    check_study_mode_limit,
    increment_study_mode_usage,
    get_study_mode_count_today,
    save_document,
)
from services.rag_service import rag_qa_pipeline
from services.study_engine import (
    QuizSession,
    FlashcardSession,
    time_to_readable,
)
from services.study_analytics import (
    record_quiz_completion,
    record_flashcard_completion,
)
from services.coin_service import (
    get_coin_balance,
    add_coins,
    spend_coins,
    reward_quiz_complete,
    reward_streak,
    reward_share,
    get_transaction_history,
    COIN_PACKAGES,
)
from services.zalopay_service import (
    create_zalopay_order,
    verify_zalopay_callback,
)

PRODUCT_NAME = config.PRODUCT_NAME

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
ZALO_DELETE_PAYLOAD = "XOA"
ZALO_BUTTON_TITLE_MAX = 22
NAMESPACE_SUMMARY = "SUMMARY_"
NAMESPACE_MORE = "MORE_"
MAX_QA_QUESTIONS_PER_DAY = 5
QA_LIMIT_PER_DOC = 5  # 5 câu Q&A mỗi document

# ═══════════════════════════════════════════════════════════════
# TOKEN MANAGEMENT (v3 — fix triệt để token bị ghi đè sau redeploy)
# ═══════════════════════════════════════════════════════════════

# Load tokens: ưu tiên DB > env vars (Railway Dashboard)
# DB = token mới nhất (từ auto-refresh hoặc /api/update-tokens)
# ENV = token cũ set trong Railway Dashboard (có thể đã hết hạn từ lâu)
_env_access = os.getenv("ZALO_OA_ACCESS_TOKEN", "")
_env_refresh = os.getenv("ZALO_REFRESH_TOKEN", "")
ZALO_OA_ACCESS_TOKEN, ZALO_REFRESH_TOKEN = load_tokens(_env_access, _env_refresh)

# CHỈ lưu env vào DB khi DB TRỐNG (tức lần deploy đầu tiên duy nhất)
# KHÔNG BAO GIỜ ghi đè DB bằng env vars — vì env vars luôn cũ hơn DB
_db_has_access = load_token("zalo_access_token") != ""
if not _db_has_access and _env_access:
    logger.info("🆕 First deploy detected — seeding DB with env vars")
    save_tokens(_env_access, _env_refresh)

logger.info("Loaded tokens — Access: %s chars (ends: ...%s), Refresh: %s chars (ends: ...%s)",
            len(ZALO_OA_ACCESS_TOKEN), ZALO_OA_ACCESS_TOKEN[-8:] if len(ZALO_OA_ACCESS_TOKEN) > 8 else "***",
            len(ZALO_REFRESH_TOKEN), ZALO_REFRESH_TOKEN[-8:] if len(ZALO_REFRESH_TOKEN) > 8 else "***")

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
user_qa_usage: dict[str, dict[str, int | str]] = {}  # Q&A quota tracking
latest_summary_by_user: dict[str, dict[str, Any]] = {}
last_image_url_by_user: dict[str, str] = {}  # Lưu URL ảnh gần nhất để trích xuất chữ khi cần
_token_lock = asyncio.Lock()

# Tối ưu chống spam: cooldown giữa các tin nhắn
user_cooldowns: dict[str, float] = {}
user_warnings: dict[str, float] = {}
COOLDOWN_SECONDS = 15

# Study Mode: Active sessions (in-memory + DB backup)
study_sessions: dict[str, dict] = {}  # user_id -> serialized session dict

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


def check_qa_limit(user_id: str) -> bool:
    """Kiểm tra user còn quyền hỏi Q&A hôm nay không."""
    today = time.strftime("%Y-%m-%d")
    if user_id not in user_qa_usage:
        user_qa_usage[user_id] = {"date": today, "count": 0}
    if user_qa_usage[user_id]["date"] != today:
        user_qa_usage[user_id] = {"date": today, "count": 0}
    return int(user_qa_usage[user_id]["count"]) < MAX_QA_QUESTIONS_PER_DAY


def increment_qa_usage(user_id: str):
    """Tăng Q&A usage count cho user."""
    today = time.strftime("%Y-%m-%d")
    if user_id not in user_qa_usage or user_qa_usage[user_id]["date"] != today:
        user_qa_usage[user_id] = {"date": today, "count": 0}
    user_qa_usage[user_id]["count"] = int(user_qa_usage[user_id]["count"]) + 1


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






def truncate_button_title(title: str, max_len: int = ZALO_BUTTON_TITLE_MAX) -> str:
    """Cắt title button cho phù hợp với giới hạn Zalo (emoji + text)."""
    if len(title) <= max_len:
        return title
    # Cắt ở giữa từ, tránh cắt giữa emoji sequence
    return title[: max_len - 1].rstrip() + "…"


# ═══════════════════════════════════════════════════════════════
# BUTTON BUILDERS
# ═══════════════════════════════════════════════════════════════

def build_point_buttons(
    points: list[dict[str, Any]],
    payload_prefix: str = "",
    namespace: str = NAMESPACE_SUMMARY,
) -> list[dict[str, str]]:
    buttons: list[dict[str, str]] = []
    for point in points:
        # Namespace để phân biệt context (summary vs more-points)
        raw_payload = f"{namespace}{payload_prefix}{point['index']}".strip()
        payload = raw_payload

        # Truncate title để đảm bảo Zalo display không bị cắt
        raw_title = f"📌 Ý {point['index']}"
        title = truncate_button_title(raw_title)

        buttons.append({
            "title": title,
            "type": "oa.query.show",
            "payload": payload,
        })
    return buttons


def build_summary_buttons(structured_summary: dict[str, Any]) -> list[dict[str, str]]:
    """Build buttons: point buttons + Study Mode (if education) + Q&A + Delete."""
    points = get_summary_points(structured_summary)
    primary_points = points[:ZALO_PRIMARY_POINT_BUTTONS]
    buttons = build_point_buttons(primary_points, namespace=NAMESPACE_SUMMARY)

    doc_type = structured_summary.get("document_type", "")
    is_study = doc_type == "education"

    # ── Study Mode: Prioritize Quiz & Flashcard ──
    if is_study:
        # Q&A trigger
        if len(buttons) < ZALO_MAX_BUTTONS:
            buttons.append({
                "title": "❓ Hỏi thêm",
                "type": "oa.query.show",
                "payload": "HỎI THÊM",
            })
        # Quiz button
        if len(buttons) < ZALO_MAX_BUTTONS:
            buttons.append({
                "title": "🎮 Làm quiz",
                "type": "oa.query.show",
                "payload": "STUDY_START_QUIZ",
            })
        # Flashcard button
        if len(buttons) < ZALO_MAX_BUTTONS:
            buttons.append({
                "title": "🗂️ Tạo flashcard",
                "type": "oa.query.show",
                "payload": "STUDY_START_FLASHCARD",
            })
    else:
        # Non-study: standard layout
        if len(points) > ZALO_PRIMARY_POINT_BUTTONS and len(buttons) < ZALO_MAX_BUTTONS:
            buttons.append({
                "title": "📚 Ý còn lại",
                "type": "oa.query.show",
                "payload": ZALO_SHOW_MORE_PAYLOAD,
            })
        if len(buttons) < ZALO_MAX_BUTTONS:
            buttons.append({
                "title": "❓ Hỏi thêm",
                "type": "oa.query.show",
                "payload": "HỎI THÊM",
            })

    # Delete button (always)
    if len(buttons) < ZALO_MAX_BUTTONS:
        buttons.append({
            "title": "🗑️ Xóa tài liệu",
            "type": "oa.query.show",
            "payload": ZALO_DELETE_PAYLOAD,
        })

    return buttons


def build_more_points_buttons(structured_summary: dict[str, Any]) -> list[dict[str, str]]:
    """Build buttons for remaining points + back button."""
    points = get_summary_points(structured_summary)[ZALO_PRIMARY_POINT_BUTTONS:]
    buttons = build_point_buttons(points[: ZALO_MAX_BUTTONS - 1], namespace=NAMESPACE_MORE)
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
    """Format bản tóm tắt chính."""
    points = get_summary_points(structured_summary)
    lines: list[str] = []

    # Document type badge
    doc_type = structured_summary.get("document_type", "")
    if doc_type:
        type_label = get_doc_type_label(doc_type)
        lines.append(f"{type_label}")

    # Header
    if elapsed_seconds is not None:
        lines.append(f"✅ Đọc xong trong {elapsed_seconds:.0f}s!")
    else:
        lines.append("✅ Đọc xong!")
    lines.append(f"📄 {title}")
    lines.append("──────────────────")

    # Overview
    overview = structured_summary.get("overview", "")
    if overview:
        lines.append(f"\n📌 {overview}\n")

    # Points list
    lines.append(f"📋 {len(points)} ý chính:")
    for point in points:
        lines.append(f"  {point['index']}. {point['title']}")
        lines.append(f"     → {clean_preview_text(point['brief'])}")

    # Action items
    action_items = structured_summary.get("action_items", [])
    if action_items:
        lines.append("")
        lines.append("🎯 Việc cần làm:")
        for item in action_items:
            lines.append(f"  • {item}")

    # Suggested questions
    suggested_questions = structured_summary.get("suggested_questions", [])
    if suggested_questions:
        lines.append("")
        lines.append("💡 Bạn có thể muốn hỏi:")
        for q in suggested_questions:
            lines.append(f"  → {q}")

    # Navigation
    lines.append("")
    lines.append("──────────────────")
    if len(points) > ZALO_PRIMARY_POINT_BUTTONS:
        lines.append(
            f"👇 Bấm nút xem chi tiết | Nhắn số {ZALO_PRIMARY_POINT_BUTTONS + 1}-{len(points)} xem thêm"
        )
    else:
        lines.append("👇 Bấm nút xem chi tiết | Nhắn NGHE 1 để nghe audio")

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
    """Format chi tiết 1 ý — dễ đọc, hấp dẫn."""
    point = structured_summary["points"][point_index - 1]
    total = len(structured_summary["points"])
    return (
        f"📝 Ý {point_index}/{total}: {point['title']}\n"
        f"──────────────────\n\n"
        f"{point['detail']}\n\n"
        f"──────────────────\n"
        f"🔊 Nhắn 'NGHE {point_index}' để nghe audio"
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
    """Welcome message v3.0 — neutral, universal."""
    return (
        f"👋 Chào bạn! Mình là {PRODUCT_NAME} — trợ lý đọc tài liệu bằng AI.\n\n"
        "📸 Chụp ảnh hoặc gửi file bất kỳ tài liệu nào:\n"
        "• Bài giảng, slide, sách\n"
        "• Hóa đơn, hợp đồng\n"
        "• Công văn, thông báo\n"
        "• Bảng tính Excel\n"
        "• Bất kỳ giấy tờ nào khó đọc\n\n"
        "⚡ Mình tóm tắt trong 15 giây — rõ ràng, dễ hiểu!\n\n"
        "🔒 Yên tâm nhé: Ảnh/file của bạn sẽ bị xóa đi ngay lập tức sau khi mình đọc xong, cực kỳ bảo mật nha!\n\n"
        "Thử gửi 1 tấm ảnh ngay nhé! 📎"
    )


def get_upload_prompt() -> str:
    return (
        "📸 Chụp ảnh tài liệu hoặc gửi file PDF/Word/Excel:\n"
        "• Bài giảng, slide, sách\n"
        "• Hóa đơn, hợp đồng, công văn\n"
        "• Bảng tính Excel\n"
        "• Bất kỳ giấy tờ nào cần tóm tắt\n\n"
        "Hoặc gửi file PDF/Word/Excel cũng được! 📎"
    )


def get_processing_message(kind: str = "tài liệu") -> str:
    return f"📖 Đang đọc {kind} cho bạn...\n⏳ Chờ xíu nhé (tầm 15s). Đọc xong mình sẽ dọn dẹp file ngay cho bạn an tâm nha! 🔒"


def get_menu_message() -> str:
    """Menu tính năng."""
    return (
        f"📖 {PRODUCT_NAME} — Trợ lý đọc tài liệu AI\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📸 GỬI ẢNH → Chụp tài liệu, mình tóm tắt trong 15 giây\n"
        "📎 GỬI FILE → PDF, Word, Excel — mình đọc và phân tích\n"
        "📋 TRICH XUAT → Trích xuất chữ từ ảnh vừa gửi\n\n"
        "⌨️ Lệnh nhanh:\n"
        "• Nhắn số 1-8 → Xem chi tiết từng ý\n"
        "• NGHE 1, NGHE 2… → Nghe audio từng ý\n"
        "• ❓ HỎI THÊM → Hỏi đáp về tài liệu vừa gửi\n"
        "• 📚 FILES → Xem danh sách tài liệu\n"
        "• XÓA → Xem & xóa tài liệu đã gửi 🔒\n"
        "• MENU → Xem bảng này\n\n"
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


async def send_summary_with_qa_buttons(
    user_id: str,
    title: str,
    structured_summary: dict[str, Any],
    elapsed_seconds: float | None = None,
):
    """Gửi tóm tắt với buttons tối ưu cho engagement.

    Layout 5 nút (Zalo max = 5):
      - Study Mode (education docs): Quiz, Flashcard
      - Q&A trigger
      - Point detail buttons
      - Suggested questions
    """
    text = format_summary_menu(title, structured_summary, elapsed_seconds)
    points = get_summary_points(structured_summary)
    suggested_questions = structured_summary.get("suggested_questions", [])
    doc_type = structured_summary.get("document_type", "")

    buttons: list[dict[str, str]] = []

    # ── Study Mode Promotion (if education/study material) ──
    if doc_type == "education":
        # Thêm nút Quiz và Flashcard
        buttons.append({
            "title": "🎮 Làm quiz",
            "type": "oa.query.show",
            "payload": "STUDY_START_QUIZ",
        })
        buttons.append({
            "title": "🗂️ Tạo flashcard",
            "type": "oa.query.show",
            "payload": "STUDY_START_FLASHCARD",
        })

    # ── Slot 1-2: Point detail buttons (tối đa 2) ──
    for point in points[:2]:
        if len(buttons) >= ZALO_MAX_BUTTONS:
            break
        raw_title = f"📌 Ý {point['index']}: {point['title'][:18]}"
        buttons.append({
            "title": truncate_button_title(raw_title),
            "type": "oa.query.show",
            "payload": f"{NAMESPACE_SUMMARY}{point['index']}",
        })

    # ── Slot: Q&A trigger (luôn có) ──
    if len(buttons) < ZALO_MAX_BUTTONS:
        buttons.append({
            "title": "❓ Hỏi thêm",
            "type": "oa.query.show",
            "payload": "HỎI THÊM",
        })

    # ── Suggested questions (nếu còn slot) ──
    max_sq = 1 if len(points) > 2 else 1
    for q in suggested_questions[:max_sq]:
        if len(buttons) >= ZALO_MAX_BUTTONS:
            break
        display = q[:25] + "…" if len(q) > 25 else q
        buttons.append({
            "title": f"💬 {display}",
            "type": "oa.query.show",
            "payload": f"HỎI: {q}",
        })

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

    # ── FILES / DANH SÁCH ──
    if normalized in {"files", "file", "danh sách", "danh sach", "liệt kê", "liet ke", "xem file", "danh sách file"}:
        await handle_files_command(user_id)
        return True

    # ── HỎI THÊM (Q&A trigger) ──
    if normalized in {"hỏi thêm", "hoi them", "hỏi thêm về file này", "hỏi thêm về file", "qa", "hỏi"}:
        # Check Q&A quota trước khi cho phép
        if not check_qa_limit(user_id):
            await send_text_message(
                user_id,
                f"⚠️ Bạn đã dùng hết {MAX_QA_QUESTIONS_PER_DAY} câu hỏi Q&A hôm nay rồi!\n\n"
                "📅 Quyền hỏi đáp sẽ được reset vào ngày mai.\n"
                "📄 Gửi tài liệu mới để được tóm tắt và hỏi thêm nhé!"
            )
            return True

        # Check document-level limit
        active_doc = get_active_doc(user_id)
        if active_doc:
            doc_id = active_doc.get("id", "")
            current_doc_count = get_qa_count(user_id, doc_id)
            if current_doc_count >= QA_LIMIT_PER_DOC:
                await send_text_message(
                    user_id,
                    f"⚠️ Bạn đã hỏi {QA_LIMIT_PER_DOC}/{QA_LIMIT_PER_DOC} câu cho tài liệu này rồi!\n\n"
                    "💡 Muốn hỏi thêm? Gửi lại file để mở phiên mới nhé.\n"
                    "Hoặc gửi tài liệu khác — mình luôn sẵn sàng! 📎"
                )
                return True

        remaining = MAX_QA_QUESTIONS_PER_DAY - int(user_qa_usage.get(user_id, {}).get("count", 0))
        set_pending_action(user_id, "qa_session", {})
        await send_text_message(
            user_id,
            f"❓ Hãy đặt câu hỏi về tài liệu này — mình sẽ phân tích và trả lời ngay!\n\n"
            f"📊 Còn {remaining} câu hỏi hôm nay."
        )
        return True

    # ── HỎI: prefix (từ suggested questions buttons) ──
    if text.strip().upper().startswith("HỎI:"):
        question = text.strip()[4:].strip()
        if question:
            await handle_qa_session(user_id, question)
            return True

    # ── XÓA DỮ LIỆU: 3 flow ──
    # "xóa" → hiện danh sách file
    # "xóa 2" → xóa file số 2
    # "xóa hết" / "xóa tất cả" → xóa toàn bộ
    import re as _re
    _xoa_match = _re.match(r'^(?:xoa|xóa)\s*(\d+)?\s*(.*)', normalized)
    if _xoa_match:
        number_part = _xoa_match.group(1)  # "2" trong "xóa 2"
        text_part = (_xoa_match.group(2) or "").strip()  # "hết" trong "xóa hết"

        # Flow 3: "xóa hết" / "xóa tất cả" / "xóa dữ liệu"
        if text_part in {"hết", "het", "tất cả", "tat ca", "dữ liệu", "du lieu", "sạch", "sach", "toàn bộ", "toan bo"}:
            delete_user_data(user_id)
            await send_text_message(
                user_id,
                "✅ Mình đã dọn dẹp sạch sẽ toàn bộ tài liệu và lịch sử của bạn rồi nhé. Mọi thứ trống trơn như mới!\n\n"
                "Bất cứ khi nào cần đọc tài liệu, bạn cứ gửi lại cho mình nha. Mình luôn ở đây! 😊"
            )
            return True

        # Lấy danh sách file của user
        docs = get_user_docs(user_id)

        # Flow 2: "xóa 2" → xóa file số 2
        if number_part:
            idx = int(number_part)
            if not docs:
                await send_text_message(
                    user_id,
                    "💭 Bạn chưa có tài liệu nào để xóa cả. Gửi ảnh hoặc file cho mình đọc trước nhé! 📸"
                )
                return True
            if idx < 1 or idx > len(docs):
                await send_text_message(
                    user_id,
                    f"❌ Số {idx} không hợp lệ. Bạn có {len(docs)} tài liệu (số 1 đến {len(docs)}).\n"
                    "Nhắn 'xóa' để xem danh sách nha!"
                )
                return True

            doc = docs[idx - 1]
            doc_name = doc.get("name", "Tài liệu")
            doc_id = doc.get("id", "")
            delete_document_by_id(user_id, doc_id)
            await send_text_message(
                user_id,
                f"🗑️ Đã xóa thành công: **{doc_name}**\n\n"
                "✅ Dữ liệu của bạn đã được dọn sạch. Yên tâm nhé! 🔒\n\n"
                "Cần xóa thêm? Nhắn 'xóa' để xem danh sách còn lại."
            )
            return True

        # Flow 1: "xóa" không có số → hiện danh sách
        if not docs:
            await send_text_message(
                user_id,
                "💭 Bạn chưa có tài liệu nào cả — không có gì cần xóa!\n\n"
                "Bất cứ khi nào cần đọc tài liệu, cứ gửi ảnh hoặc file cho mình nha! 📸"
            )
            return True

        lines = ["📚 Danh sách tài liệu của bạn:\n"]
        for i, doc in enumerate(docs, 1):
            doc_name = doc.get("name", "Tài liệu")
            doc_type = doc.get("doc_type", doc.get("type", "file"))
            icon = {"image": "🖼️", "file": "📎", "pdf": "📄"}.get(doc_type, "📄")
            lines.append(f"  {icon} {i}. {doc_name}")

        lines.append("\n🗑️ Nhắn 'xóa 1', 'xóa 2'... để xóa từng file")
        lines.append("🧹 Nhắn 'xóa hết' để xóa toàn bộ")
        lines.append("\n🔒 Dữ liệu của bạn luôn được bảo mật!")

        await send_text_message(user_id, "\n".join(lines))
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
            await send_summary_with_qa_buttons(user_id, latest["title"], latest["data"])
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

    # ── XEM CHI TIẾT TỪ BUTTON (payload với namespace) ──
    if latest:
        norm_upper = normalized.upper()
        if norm_upper.startswith(NAMESPACE_SUMMARY) or norm_upper.startswith(NAMESPACE_MORE):
            # Extract số từ payload: "SUMMARY_1" → "1"
            num_part = norm_upper.replace(NAMESPACE_SUMMARY, "").replace(NAMESPACE_MORE, "")
            if num_part.isdigit():
                point_index = int(num_part)
                if 1 <= point_index <= len(latest["data"]["points"]):
                    detail_text = format_point_detail(latest["data"], point_index)
                    detail_buttons = [
                        {"title": f"🔊 Nghe đọc Ý {point_index}", "type": "oa.query.show", "payload": f"NGHE {point_index}"},
                        {"title": "❓ Hỏi thêm về file", "type": "oa.query.show", "payload": "HỎI THÊM"},
                        {"title": "🔙 Xem tóm tắt", "type": "oa.query.show", "payload": ZALO_BACK_TO_SUMMARY_PAYLOAD},
                    ]
                    await send_long_text_message(user_id, detail_text, detail_buttons)
                    return True

    # ── XEM CHI TIẾT BẰNG SỐ (user nhắn số trực tiếp) ──
    if latest and normalized.isdigit():
        point_index = int(normalized)
        if 1 <= point_index <= len(latest["data"]["points"]):
            detail_text = format_point_detail(latest["data"], point_index)
            detail_buttons = [
                {"title": f"🔊 Nghe đọc Ý {point_index}", "type": "oa.query.show", "payload": f"NGHE {point_index}"},
                {"title": "❓ Hỏi thêm về file", "type": "oa.query.show", "payload": "HỎI THÊM"},
                {"title": "🔙 Xem tóm tắt", "type": "oa.query.show", "payload": ZALO_BACK_TO_SUMMARY_PAYLOAD},
            ]
            await send_long_text_message(user_id, detail_text, detail_buttons)
            return True

    # ── CHI TIẾT + SỐ ──
    if latest and normalized.replace("chi tiết", "chi tiet").startswith("chi tiet"):
        point_index = get_point_from_command(normalized)
        if point_index is not None and 1 <= point_index <= len(latest["data"]["points"]):
            detail_text = format_point_detail(latest["data"], point_index)
            detail_buttons = [
                {"title": f"🔊 Nghe đọc Ý {point_index}", "type": "oa.query.show", "payload": f"NGHE {point_index}"},
                {"title": "❓ Hỏi thêm về file", "type": "oa.query.show", "payload": "HỎI THÊM"},
                {"title": "🔙 Xem tóm tắt", "type": "oa.query.show", "payload": ZALO_BACK_TO_SUMMARY_PAYLOAD},
            ]
            await send_long_text_message(user_id, detail_text, detail_buttons)
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
# Q&A SESSION HANDLER
# ═══════════════════════════════════════════════════════════════

async def handle_qa_session(user_id: str, question: str):
    """Xử lý câu hỏi về document đang active — chất lượng cao."""
    # ── CHECK DAILY Q&A QUOTA (max 5 câu/ngày) ──
    if not check_qa_limit(user_id):
        await send_text_message(
            user_id,
            f"⚠️ Bạn đã dùng hết {MAX_QA_QUESTIONS_PER_DAY} câu hỏi Q&A hôm nay rồi!\n\n"
            "📅 Quyền hỏi đáp sẽ được reset vào ngày mai.\n"
            "📄 Gửi tài liệu mới để được tóm tắt và hỏi thêm nhé!"
        )
        return

    active_doc = get_active_doc(user_id)
    if not active_doc:
        await send_text_message(user_id, "⚠️ Chưa có tài liệu nào. Gửi file hoặc ảnh trước nhé!")
        return

    doc_id = active_doc.get("id", "")
    doc_title = active_doc.get("name", "tài liệu")

    # ── CHECK DOCUMENT-LEVEL Q&A LIMIT (5 câu/document) ──
    current_qa_count = get_qa_count(user_id, doc_id)
    if current_qa_count >= QA_LIMIT_PER_DOC:
        await send_text_message(
            user_id,
            f"⚠️ Bạn đã hỏi {QA_LIMIT_PER_DOC}/{QA_LIMIT_PER_DOC} câu cho tài liệu này rồi!\n\n"
            "💡 Muốn hỏi thêm? Gửi lại file để mở phiên mới nhé.\n"
            "Hoặc gửi tài liệu khác — mình luôn sẵn sàng! 📎"
        )
        return

    # Lấy text tạm thời (lưu khi tóm tắt)
    doc_text = get_document_text_temp(user_id, doc_id)
    if not doc_text:
        await send_text_message(
            user_id,
            "⚠️ Tài liệu này đã hết phiên hỏi đáp (quá 24h).\n\n"
            "📎 Gửi lại file để mình đọc và bạn có thể hỏi thêm nhé!"
        )
        return

    await send_text_message(user_id, "🤔 Đang phân tích tài liệu để trả lời...")

    answer = await answer_question_about_document(question, doc_text, doc_title)

    # ── Increment counters ──
    increment_qa_usage(user_id)  # Daily quota
    new_qa_count = increment_qa_count(user_id, doc_id)  # Document-level counter
    remaining_doc = QA_LIMIT_PER_DOC - new_qa_count
    remaining_daily = MAX_QA_QUESTIONS_PER_DAY - int(user_qa_usage[user_id]["count"])
    logger.info(f"User {user_id} Q&A: doc_count={new_qa_count}/{QA_LIMIT_PER_DOC}, daily={remaining_daily}/{MAX_QA_QUESTIONS_PER_DAY}")

    # ── Build smart follow-up buttons ──
    response = f"💡 **Trả lời:**\n\n{answer}\n\n──────────────────\n📊 Đã hỏi {new_qa_count}/{QA_LIMIT_PER_DOC} câu cho tài liệu này."

    buttons: list[dict[str, str]] = []

    # Nút "Hỏi câu khác" — CHỈ hiển thị nếu còn lượt
    if remaining_doc > 0:
        buttons.append({
            "title": f"❓ Hỏi thêm ({remaining_doc} câu còn)",
            "type": "oa.query.show",
            "payload": "HỎI THÊM",
        })

    # Lấy suggested questions từ latest summary (nếu có)
    latest = get_latest_summary(user_id)
    if latest:
        sq = latest["data"].get("suggested_questions", [])
        for q in sq[:2]:
            if len(buttons) >= 4:
                break
            # Bỏ qua câu hỏi đã hỏi rồi (so sánh fuzzy)
            if q.lower().strip("?") in question.lower():
                continue
            display = q[:30] + "…" if len(q) > 30 else q
            buttons.append({
                "title": f"💬 {display}",
                "type": "oa.query.show",
                "payload": f"HỎI: {q}",
            })

    # Nút quay lại tóm tắt + nghe audio
    buttons.append({"title": "🔙 Xem tóm tắt", "type": "oa.query.show", "payload": "XEM TOM TAT"})
    if len(buttons) < ZALO_MAX_BUTTONS:
        buttons.append({"title": "🔊 Nghe đọc Ý 1", "type": "oa.query.show", "payload": "NGHE 1"})

    await send_long_text_message(user_id, response, buttons[:ZALO_MAX_BUTTONS])

    # Gia hạn TTL mỗi khi user hỏi (keep alive thêm 24h)
    renew_document_text_temp(user_id, doc_id, ttl_hours=24)


async def handle_files_command(user_id: str):
    """Hiển thị danh sách tài liệu của user — với action buttons."""
    docs = get_user_docs(user_id)

    if not docs:
        await send_text_message(
            user_id,
            "📭 Bạn chưa có tài liệu nào.\n\n"
            "Gửi ảnh hoặc file cho mình đọc nhé! 📸"
        )
        return

    lines = [f"📚 **Tài liệu của bạn** ({len(docs)}/5):\n"]

    has_any_qa = False
    for i, doc in enumerate(docs, 1):
        name = doc.get("name", "Tài liệu")
        doc_type = doc.get("doc_type", doc.get("type", "file"))
        icon = {"image": "🖼️", "file": "📎", "pdf": "📄"}.get(doc_type, "📄")
        doc_id = doc.get("id", "")
        has_qa = get_document_text_temp(user_id, doc_id) is not None
        if has_qa:
            has_any_qa = True
        qa_badge = " 💬" if has_qa else ""
        lines.append(f"  {icon} {i}. {name}{qa_badge}")

    lines.append("\n💬 = còn hỏi đáp được (24h)")

    # ── Build action buttons ──
    buttons: list[dict[str, str]] = []

    if has_any_qa:
        buttons.append({
            "title": "❓ Hỏi về tài liệu",
            "type": "oa.query.show",
            "payload": "HỎI THÊM",
        })

    buttons.append({
        "title": "🗑️ Xóa tài liệu",
        "type": "oa.query.show",
        "payload": "XOA",
    })

    if len(docs) > 1:
        buttons.append({
            "title": "🧹 Xóa tất cả",
            "type": "oa.query.show",
            "payload": "xóa hết",
        })

    await send_text_with_buttons(user_id, "\n".join(lines), buttons[:ZALO_MAX_BUTTONS])


# ═══════════════════════════════════════════════════════════════
# FASTAPI APP SETUP
# ═══════════════════════════════════════════════════════════════

app = FastAPI(title=f"{PRODUCT_NAME} — Trợ lý đọc tài liệu AI")

@app.middleware("http")
async def catch_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/audio", StaticFiles(directory=config.AUDIO_DIR), name="audio")

HOMEPAGE_HTML = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta name="zalo-platform-site-verification" content="{ZALO_VERIFICATION_CODE}" />
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{PRODUCT_NAME} — Trợ lý đọc tài liệu AI</title>
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
<h1>📖 {PRODUCT_NAME}</h1>
<p>Trợ lý AI đọc hiểu và tóm tắt tài liệu</p>
<p class="status">● Server đang hoạt động</p>
<div>
<span class="badge">📸 Ảnh → Tóm tắt</span>
<span class="badge">📄 PDF/Word</span>
<span class="badge">🔊 Audio TTS</span>
<span class="badge">📋 OCR</span>
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

@app.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "Server is running"}
async def health():
    return HTMLResponse(content=HOMEPAGE_HTML, status_code=200)


@app.get(f"/zalo_verifier{ZALO_VERIFICATION_CODE}.html", response_class=HTMLResponse)
async def zalo_verifier():
    return HTMLResponse(content=VERIFIER_HTML, status_code=200)


@app.get("/webhook/zalo")
async def webhook_verify():
    return JSONResponse(content={"status": "ok", "message": f"{PRODUCT_NAME} webhook active"}, status_code=200)


@app.get("/debug/tokens")
async def debug_tokens(request: Request):
    """Endpoint debug: xem trạng thái token hiện tại."""
    supplied_secret = request.headers.get("x-debug-secret", "") or request.query_params.get("secret", "")
    if not config.DEBUG_ADMIN_SECRET or supplied_secret != config.DEBUG_ADMIN_SECRET:
        raise HTTPException(status_code=404, detail="Not found")
    info = get_token_info()
    info["memory_access_token_len"] = len(ZALO_OA_ACCESS_TOKEN)
    info["memory_refresh_token_len"] = len(ZALO_REFRESH_TOKEN)
    # So sánh env vs memory để biết token đang dùng từ nguồn nào
    env_refresh = os.getenv("ZALO_REFRESH_TOKEN", "")
    info["token_source"] = "DB" if ZALO_REFRESH_TOKEN != env_refresh else "ENV"
    info["version"] = "2.0-core"
    info["features"] = ["summarization", "ocr", "doc_classification", "tts"]
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
                if not text and _ft == "pdf":
                    # OCR fallback for scanned/handwritten PDF
                    page_images = await convert_pdf_to_images(file_path, max_pages=10)
                    if not page_images:
                        return JSONResponse(content={"error": "Không thể đọc file PDF này (scan/ảnh)."}, status_code=400)
                    try:
                        structured = await summarize_pdf_images_structured(page_images)
                    finally:
                        for img_path in page_images:
                            try:
                                os.remove(img_path)
                            except OSError:
                                pass
                elif not text:
                    return JSONResponse(content={"error": "Không đọc được nội dung file này."}, status_code=400)
                else:
                    structured = await summarize_text_structured(text)

            if structured.get("error"):
                return JSONResponse(content={"error": str(structured["error"])}, status_code=500)

            return JSONResponse(content=structured, status_code=200)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as exc:
        logger.error("API summarize error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": "Đã xảy ra lỗi. V vui lòng thử lại!"}, status_code=500)


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
                if not text and _ft == "pdf":
                    page_images = await convert_pdf_to_images(file_path, max_pages=10)
                    if not page_images:
                        return HTMLResponse(content="<h1>Không thể đọc file PDF này (scan/ảnh).</h1>", status_code=400)
                    try:
                        structured = await summarize_pdf_images_structured(page_images)
                    finally:
                        for img_path in page_images:
                            try:
                                os.remove(img_path)
                            except OSError:
                                pass
                elif not text:
                    return HTMLResponse(content="<h1>Không đọc được nội dung file này.</h1>", status_code=400)
                else:
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



        if event_name == "follow":
            await send_text_message(sender_id, get_welcome_message())
            return

        if event_name == "user_send_text":
            await handle_zalo_text(sender_id, body.get("message", {}).get("text", ""))
            return

        if event_name == "user_send_image":
            attachments = body.get("message", {}).get("attachments", [])
            if attachments:
                await handle_zalo_image(sender_id, attachments[0].get("payload", {}).get("url", ""))
            return

        if event_name == "user_send_file":
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
# AI-POWERED SMART CHAT
# ═══════════════════════════════════════════════════════════════

CHAT_SYSTEM_PROMPT = f"""Bạn là {PRODUCT_NAME} — trợ lý AI đọc và tóm tắt tài liệu trên Zalo.

TÍNH CÁCH:
- Thân thiện, ấm áp, gần gũi như một người bạn thông minh
- Dùng emoji vừa phải (1-3 emoji/tin nhắn), tự nhiên không gượng ép
- Xưng "mình", gọi người dùng "bạn"
- Trả lời ngắn gọn (tối đa 3-5 câu), KHÔNG dài dòng

KHẢ NĂNG CỦA BẠN (chỉ nhắc khi phù hợp):
📸 Đọc ảnh chụp tài liệu (slide, sách, hóa đơn, giấy tờ)
📄 Tóm tắt file PDF, Word (.doc, .docx), Excel (.xlsx)
🔊 Đọc tóm tắt thành audio
❓ Hỏi đáp về nội dung tài liệu đã gửi
📋 Trích xuất chữ từ ảnh (OCR)

QUY TẮC QUAN TRỌNG:
1. LUÔN trả lời bằng tiếng Việt có dấu.
2. Nếu user chào hỏi → chào lại ấm áp, giới thiệu ngắn gọn mình làm gì.
3. Nếu user hỏi "bạn là ai / giúp gì / làm gì" → giới thiệu khả năng một cách tự nhiên.
4. Nếu user cảm ơn / khen → đáp lại vui vẻ, khiêm tốn.
5. Nếu user hỏi kiến thức chung (toán, lý, hóa, lịch sử, v.v.) → trả lời TỪ CHỐI nhẹ nhàng, giải thích mình chuyên đọc tài liệu, gợi ý gửi file/ảnh.
6. Nếu user nhắn linh tinh / không rõ → trả lời thân thiện, gợi ý thử gửi tài liệu.
7. KHÔNG BAO GIỜ bịa đặt thông tin kiến thức. Không trả lời câu hỏi ngoài phạm vi đọc tài liệu.
8. KHÔNG BAO GIỜ giả vờ là ChatGPT, Google, hoặc AI khác.
9. Cuối mỗi câu trả lời, nhẹ nhàng gợi ý gửi ảnh/file nếu phù hợp ngữ cảnh (đừng ép buộc).
10. Trả lời plain text (KHÔNG dùng markdown **bold**, KHÔNG dùng JSON). Chỉ dùng emoji."""


async def _handle_smart_chat(user_id: str, text: str):
    """Xử lý tin nhắn chat ngắn bằng AI — trả lời thông minh, linh hoạt."""
    try:
        result = await _call_with_smart_routing(
            content=f"Tin nhắn từ người dùng Zalo:\n\n\"{text}\"\n\nHãy trả lời ngắn gọn, thân thiện (tối đa 4-5 câu).",
            text_length=len(text),
            max_tokens=512,
            response_json=False,  # Trả về text thuần, không JSON
            system_prompt=CHAT_SYSTEM_PROMPT,
        )

        if result and result.strip():
            # Clean up: remove markdown formatting if AI accidentally used it
            clean_result = result.strip()
            clean_result = clean_result.replace("**", "").replace("```", "")
            # Truncate if too long (Zalo message limit)
            if len(clean_result) > 1000:
                clean_result = clean_result[:997] + "..."
            await send_text_message(user_id, clean_result)
        else:
            # Fallback nếu AI không trả về gì
            await send_text_message(
                user_id,
                f"😊 Mình là {PRODUCT_NAME} — trợ lý đọc tài liệu AI!\n\n"
                "Gửi ảnh hoặc file tài liệu cho mình — mình tóm tắt ngay nhé! 📸📄"
            )
    except Exception as exc:
        logger.warning("Smart chat error: %s — using fallback", exc)
        await send_text_message(
            user_id,
            f"😊 Mình là {PRODUCT_NAME}! Gửi ảnh hoặc file tài liệu cho mình — mình đọc và tóm tắt giúp bạn! 📸"
        )


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

        # ── Q&A SESSION: User đang hỏi về tài liệu ──
        if action == "qa_session":
            clear_pending_action(user_id)
            await handle_qa_session(user_id, text)
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

    # Lệnh tương tác (menu, số, nghe, chi tiết...)
    if await handle_interactive_command(user_id, normalized):
        return

    # ═══════════════════════════════════════════════════════════════
    # STUDY MODE: Quiz & Flashcard
    # ═══════════════════════════════════════════════════════════════

    # ── Check for active study session ──
    session_record = load_study_session(user_id)
    if session_record:
        session_type = session_record["session_type"]
        session_data = session_record["data"]

        if session_type == "quiz":
            # Continuing quiz session
            await handle_quiz_answer(user_id, normalized, session_data)
            return
        elif session_type == "flashcard":
            # Continuing flashcard session
            await handle_flashcard_action(user_id, normalized, session_data)
            return

    # ── Start new study session ──
    # Commands: quiz, flashcards, luyện tập, ôn tập
    study_keywords = {"quiz", "quizz", "câu hỏi", "trắc nghiệm", "luyện tập", "ôn tập", "flashcard", "thẻ", "cards"}
    if any(kw in normalized for kw in study_keywords):
        # Check if user has active document
        active_doc = get_active_doc_id(user_id)
        if not active_doc:
            await send_text_message(
                user_id,
                "⚠️ Bạn chưa gửi tài liệu nào để luyện tập.\n\n"
                "Gửi ảnh hoặc file PDF/Word trước nhé! 📚"
            )
            return

        # Get document text for context
        doc_text = get_document_text_temp(user_id, active_doc)
        if not doc_text:
            await send_text_message(
                user_id,
                "⚠️ Tài liệu đã hết hạn hoặc không tìm thấy.\n\n"
                "Vui lòng gửi lại tài liệu để bắt đầu ôn tập nhé!"
            )
            return

        # Check premium (if needed) —暂时 free for now
        # if not check_study_premium(user_id):
        #     await send_study_premium_upsell(user_id)
        #     return

        # Detect mode should already be STUDY_MATERIAL from earlier processing
        # But we can re-check quickly
        await start_quiz_session(user_id, doc_text)
        return

    # ═══════════════════════════════════════════════════════════════
    # END STUDY MODE
    # ═══════════════════════════════════════════════════════════════

    # Lệnh tương tác (menu, số, nghe, chi tiết...)
    if await handle_interactive_command(user_id, normalized):
        return

    # ── AI-POWERED CHAT: Trả lời thông minh như AI thật ──
    # Text ngắn (< 200 ký tự) → gửi qua AI với prompt "chat mode"
    # Text dài (≥ 200 ký tự) → xử lý như tài liệu cần tóm tắt
    if len(text.strip()) < 200:
        await _handle_smart_chat(user_id, text)
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
    # Lưu text gốc cho Q&A (TTL 24h)
    doc_id = str(uuid.uuid4().hex[:12])
    save_document_text_temp(user_id, doc_id, text, ttl_hours=24)
    # Set active doc để Q&A hoạt động
    set_active_doc(user_id, doc_id)
    # Reset Q&A counter cho document mới
    reset_qa_count(user_id, doc_id)
    await send_summary_with_qa_buttons(user_id, "văn bản bạn vừa gửi", structured)
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
            "Mình chỉ hỗ trợ file PDF, Word (.docx), Excel (.xlsx), hoặc ảnh. Vui lòng gửi đúng định dạng!"
        )
        return

    # Check for .xls legacy (Excel 2003) — require .xlsx
    if get_file_type(file_name) == "xls_legacy":
        await send_text_message(
            user_id,
            "📊 File .xls (Excel cũ) — mình cần file .xlsx nhé!\n\n"
            "Mở file → Save As → chọn .xlsx → gửi lại 😊"
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
        if not text and _file_type == "pdf":
            # ── FALLBACK: PDF scan/handwritten → convert to images → Gemini Vision ──
            logger.info("PDF text extraction empty — trying OCR fallback via Gemini Vision")
            await send_text_message(
                user_id,
                "📷 File PDF này là dạng scan/ảnh chụp. Đang dùng AI Vision để đọc..."
            )
            page_images = await convert_pdf_to_images(file_path, max_pages=10)
            if not page_images:
                await send_text_message(
                    user_id,
                    "Không thể đọc file PDF này. File có thể bị lỗi hoặc được bảo vệ bằng mật khẩu."
                )
                return

            try:
                structured = await summarize_pdf_images_structured(page_images)
                if structured.get("error"):
                    await send_text_message(user_id, str(structured["error"]))
                    return

                remember_summary(user_id, file_name, structured)
                # Lưu text gốc từ PDF scan (text từ OCR) — TTL 24h
                # Lưu ý: PDF scan không có raw text, lưu empty string hoặc OCR text nếu có
                doc_id = str(uuid.uuid4().hex[:12])
                # Vì PDF scan không có text, ta lưu placeholder để track doc existence
                save_document_text_temp(user_id, doc_id, "", ttl_hours=24)
                # Set active doc để Q&A hoạt động (dù không có raw text, vẫn có thể hỏi về summary)
                set_active_doc(user_id, doc_id)
                # Reset Q&A counter cho document mới
                reset_qa_count(user_id, doc_id)
                await send_summary_with_interactive_buttons(
                    user_id, file_name, structured, time.time() - start_time
                )
                increment_usage(user_id)
                return
            finally:
                # Cleanup temporary page images
                for img_path in page_images:
                    try:
                        os.remove(img_path)
                    except OSError:
                        pass

        elif not text:
            # Give more specific guidance for .doc legacy files
            if _file_type == "doc_legacy":
                await send_text_message(
                    user_id,
                    "📄 File .doc (Word cũ) này mình chưa đọc được nội dung.\n\n"
                    "💡 Thử 1 trong 2 cách:\n"
                    "1️⃣ Mở file → Save As → chọn .docx → gửi lại\n"
                    "2️⃣ Chụp ảnh từng trang tài liệu → gửi ảnh cho mình 📸"
                )
            else:
                await send_text_message(
                    user_id,
                    "Không đọc được nội dung file này. Thử chụp ảnh tài liệu và gửi ảnh cho mình!"
                )
            return

        structured = await summarize_text_structured(text)
        if structured.get("error"):
            await send_text_message(user_id, str(structured["error"]))
            return

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

        remember_summary(user_id, file_name, structured)
        # Lưu text gốc cho Q&A (TTL 24h)
        doc_id = str(uuid.uuid4().hex[:12])
        save_document_text_temp(user_id, doc_id, text, ttl_hours=24)
        # Set active doc để Q&A hoạt động
        set_active_doc(user_id, doc_id)
        # Reset Q&A counter cho document mới
        reset_qa_count(user_id, doc_id)
        await send_summary_with_qa_buttons(user_id, file_name, structured, time.time() - start_time)
        increment_usage(user_id)
    except Exception as exc:
        logger.error("File processing error: %s", exc, exc_info=True)
        await send_text_message(user_id, "Đã xảy ra lỗi. Vui lòng thử lại!")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def handle_zalo_image(user_id: str, image_url: str):
    """Xử lý ảnh từ user — tóm tắt + nút trích xuất chữ."""
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

        # ── AI Summary ──
        structured = await summarize_image_structured(image_path)
        if structured.get("error"):
            await send_text_message(user_id, str(structured["error"]))
            return

        doc_type = structured.get("document_type", "general")

        # ═══ ẢNH THƯỜNG: Redirect ═══
        if doc_type == "photo":
            photo_redirects = [
                (
                    "📷 Ảnh này không phải tài liệu rồi!\n\n"
                    "Mình chuyên đọc:\n"
                    "• 📚 Bài giảng, slide → Tóm tắt nhanh\n"
                    "• 📄 Hợp đồng, công văn → Phân tích chi tiết\n"
                    "• 🧾 Hóa đơn → Kiểm tra số liệu\n\n"
                    "📸 Chụp ảnh tài liệu gửi thử nhé!"
                ),
                (
                    "🖼️ Ảnh đẹp! Nhưng mình đọc TÀI LIỆU mới giỏi 😄\n\n"
                    "Thử chụp ảnh slide bài giảng, sách, hóa đơn, hoặc giấy tờ bất kỳ gửi mình — tóm tắt trong 15 giây! ⚡"
                ),
                (
                    "📷 Mình cần ảnh TÀI LIỆU nhé — không phải ảnh chụp thông thường!\n\n"
                    "Ví dụ: slide PowerPoint, trang sách, hóa đơn, hợp đồng, công văn...\n"
                    "📸 Gửi thử 1 tấm xem mình phân tích!"
                ),
            ]
            await send_text_message(user_id, random.choice(photo_redirects))
            return

        # ═══ TÓM TẮT THÔNG THƯỜNG ═══
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

    except Exception as exc:
        logger.error("Image processing error: %s", exc, exc_info=True)
        await send_text_message(user_id, "Không đọc được ảnh. Chụp rõ hơn và thử lại!")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


# ═══════════════════════════════════════════════════════════════
# STUDY MODE: Quiz & Flashcard Handlers
# ═══════════════════════════════════════════════════════════════

async def start_quiz_session(user_id: str, doc_text: str):
    """Bắt đầu quiz session từ document text."""
    try:
        increment_sessions_started()  # Track session start

        # Check premium limit
        if not check_study_mode_limit(user_id):
            # Premium gating: user đã hết free sessions
            used = get_study_mode_count_today(user_id)
            await send_text_message(
                user_id,
                f"⚠️ Bạn đã sử dụng hết {used}/{config.FREE_STUDY_SESSIONS_PER_DAY} lần luyện tập miễn phí hôm nay.\n\n"
                "🎯 Đăng ký Premium để học tập không giới hạn:\n"
                "• ❤️‍🔥 Quiz & Flashcard không giới hạn\n"
                "• 📚 Tài liệu cao cấp\n"
                "• 🚀 Ưu tiên AI tốc độ cao\n\n"
                "👉 Nhắn 'PREMIUM' để biết thêm chi tiết!"
            )
            return

        # Increment usage
        increment_study_mode_usage(user_id)

        # Gọi Gemini để tạo quiz questions
        prompt = GENERATE_QUIZ_PROMPT.format(document_text=doc_text[:8000])
        quiz_json_str = await _call_with_smart_routing(
            prompt,
            text_length=len(doc_text),
            max_tokens=8192,
            response_json=True,
            force_gemini=False,
        )

        # Parse JSON
        quiz_data = json.loads(quiz_json_str)
        questions = quiz_data.get("questions", [])

        if not questions:
            await send_text_message(user_id, "❌ Không thể tạo quiz từ tài liệu này. Tài liệu có thể không chứa nội dung trắc nghiệm.")
            return

        # Tạo QuizSession
        session = QuizSession(
            questions=questions,
            doc_id=get_active_doc(user_id) or "unknown",
        )
        session.start()

        # Lưu session vào DB
        save_study_session(user_id, session.doc_id, "quiz", session.to_dict())

        # Gửi câu hỏi đầu tiên
        await send_quiz_question(user_id, session)

    except json.JSONDecodeError as e:
        logger.error(f"Quiz generation JSON parse error: {e}")
        await send_text_message(user_id, "❌ Lỗi khi tạo quiz. Vui lòng thử lại!")
    except Exception as e:
        logger.error(f"Start quiz session error: {e}")
        await send_text_message(user_id, "❌ Lỗi khi bắt đầu quiz. Vui lòng thử lại!")


async def send_quiz_question(user_id: str, session: QuizSession):
    """Gửi câu hỏi quiz hiện tại với buttons."""
    text = session.format_question()
    buttons = session.get_buttons()

    # Thêm nút thoát/ xem điểm
    abort_buttons = session.get_abort_buttons()
    if len(buttons) + len(abort_buttons) <= 5:
        buttons.extend(abort_buttons)
    else:
        # Nếu vượt quá 5 nút, chỉ giữ 4 answer + 1 exit
        buttons = buttons[:4]
        buttons.append({
            "title": "⏹️ Thoát",
            "type": "oa.query.show",
            "payload": "QUIZ_EXIT",
        })

    await send_long_text_message(user_id, text, buttons)


async def handle_quiz_answer(user_id: str, user_input: str, session_data: dict):
    """Xử lý câu trả lời quiz từ user."""
    try:
        # Restore session
        session = QuizSession.from_dict(session_data)

        # Check if user wants to exit or check score
        normalized = user_input.strip().upper()
        if normalized == "THOÁT" or normalized == "QUIZ_EXIT":
            clear_study_session(user_id)
            final = session.get_final_score()
            score_text = (
                f"📊 **Kết quả quiz**\n\n"
                f"✅ Đúng: {final['correct']}/{final['total']}\n"
                f"📈 Điểm: {final['percentage']:.1f}%\n"
                f"🏅 Đánh giá: {final['grade']}\n"
                f"🔥 Chuỗi đúng: {final['streak']}"
            )
            if "time_seconds" in final:
                score_text += f"\n⏱️ Thời gian: {final['time_seconds']} giây"
            await send_text_message(user_id, score_text)
            return

        if normalized == "XEM ĐIỂM" or normalized == "QUIZ_SCORE":
            current_score = f"📈 Tiến độ hiện tại:\n✅ Đúng: {session.score}/{session.current_idx}\n🔥 Chuỗi: {session.streak}"
            await send_text_message(user_id, current_score)
            # Không tiếp tục xử lý, giữ session sống
            return

        # Process answer (A/B/C/D)
        if normalized not in {"A", "B", "C", "D"}:
            await send_text_message(user_id, "⚠️ Vui lòng trả lời A, B, C, hoặc D. Hoặc bấm nút bên dưới!")
            return

        result = session.process_answer(normalized)

        # Feedback
        feedback = f"{result['feedback_text']}\n"
        if result['explanation']:
            feedback += f"\n💡 Giải thích: {result['explanation']}"

        await send_text_message(user_id, feedback)

        # Next question or finish
        if result['is_last']:
            # Quiz completed
            clear_study_session(user_id)
            final = session.get_final_score()
            # Record analytics
            record_quiz_completion(
                user_id=user_id,
                score=final['correct'],
                total=final['total'],
                time_seconds=final.get('time_seconds', 0)
            )
            score_text = (
                f"🎉 **Hoàn thành quiz!**\n\n"
                f"✅ Đúng: {final['correct']}/{final['total']}\n"
                f"📈 Điểm: {final['percentage']:.1f}%\n"
                f"🏅 Đánh giá: {final['grade']}\n"
                f"🔥 Chuỗi đúng cao nhất: {final['streak']}"
            )
            if "time_seconds" in final:
                score_text += f"\n⏱️ Thời gian: {time_to_readable(final['time_seconds'])}"

            buttons = [
                {"title": "🔄 Làm lại", "type": "oa.query.show", "payload": "STUDY_START_QUIZ"},
                {"title": "📊 Tiến độ", "type": "oa.query.show", "payload": "STUDY_PROGRESS"},
                {"title": "🔙 Menu", "type": "oa.query.show", "payload": "MENU"},
            ]
            await send_long_text_message(user_id, score_text, buttons)
        else:
            # Save updated session and send next question
            save_study_session(user_id, session.doc_id, "quiz", session.to_dict())
            await send_quiz_question(user_id, session)

    except Exception as e:
        logger.error(f"Handle quiz answer error: {e}")
        await send_text_message(user_id, "❌ Lỗi xử lý câu trả lời. Vui lòng thử lại!")


async def start_flashcard_session(user_id: str, doc_text: str):
    """Bắt đầu flashcard session từ document text."""
    try:
        increment_sessions_started()  # Track session start

        # Check premium limit
        if not check_study_mode_limit(user_id):
            # Premium gating: user đã hết free sessions
            used = get_study_mode_count_today(user_id)
            await send_text_message(
                user_id,
                f"⚠️ Bạn đã sử dụng hết {used}/{config.FREE_STUDY_SESSIONS_PER_DAY} lần luyện tập miễn phí hôm nay.\n\n"
                "🎯 Đăng ký Premium để học tập không giới hạn:\n"
                "• ❤️‍🔥 Quiz & Flashcard không giới hạn\n"
                "• 📚 Tài liệu cao cấp\n"
                "• 🚀 Ưu tiên AI tốc độ cao\n\n"
                "👉 Nhắn 'PREMIUM' để biết thêm chi tiết!"
            )
            return

        # Increment usage
        increment_study_mode_usage(user_id)

        # Gọi Gemini để tạo flashcards
        prompt = GENERATE_FLASHCARD_PROMPT.format(document_text=doc_text[:8000])
        flashcard_json_str = await _call_with_smart_routing(
            prompt,
            text_length=len(doc_text),
            max_tokens=8192,
            response_json=True,
            force_gemini=False,
        )

        flashcard_data = json.loads(flashcard_json_str)
        flashcards = flashcard_data.get("flashcards", [])

        if not flashcards:
            await send_text_message(user_id, "❌ Không thể tạo flashcard từ tài liệu này.")
            return

        # Tạo FlashcardSession
        session = FlashcardSession(
            flashcards=flashcards,
            doc_id=get_active_doc(user_id) or "unknown",
        )

        # Lưu session
        save_study_session(user_id, session.doc_id, "flashcard", session.to_dict())

        # Gửi card đầu tiên
        await send_flashcard_front(user_id, session)

    except json.JSONDecodeError as e:
        logger.error(f"Flashcard generation JSON parse error: {e}")
        await send_text_message(user_id, "❌ Lỗi khi tạo flashcard. Vui lòng thử lại!")
    except Exception as e:
        logger.error(f"Start flashcard session error: {e}")
        await send_text_message(user_id, "❌ Lỗi khi bắt đầu flashcard. Vui lòng thử lại!")


async def send_flashcard_front(user_id: str, session: FlashcardSession):
    """Gửi mặt trước flashcard với nút Lật."""
    text = session.format_card_front()
    buttons = session.get_front_buttons()
    await send_long_text_message(user_id, text, buttons)


async def send_flashcard_back(user_id: str, session: FlashcardSession):
    """Gửi mặt sau flashcard với nút Nhớ/Chưa nhớ."""
    text = session.format_card_back()
    buttons = session.get_back_buttons()
    await send_long_text_message(user_id, text, buttons)


async def handle_flashcard_action(user_id: str, user_input: str, session_data: dict):
    """Xử lý actions trong flashcard session."""
    try:
        session = FlashcardSession.from_dict(session_data)
        normalized = user_input.strip().upper()

        # Map payloads to actions
        action_map = {
            "FC_FLIP": "flip",
            "FC_SKIP": "skip",
            "FC_EXIT": "exit",
            "FC_REMEMBER": "remember",
            "FC_FORGOT": "forgot",
            "FC_NEXT": "next",
        }

        # Determine action
        action = None
        for payload, act in action_map.items():
            if normalized == payload or (normalized == "LẤT" and act == "flip"):
                action = act
                break

        if not action:
            await send_text_message(user_id, "⚠️ Vui lòng bấm nút bên dưới hoặc nhắn 'LẤT', 'NHỚ', 'CHƯA NHỚ'.")
            return

        # Handle actions
        if action == "exit":
            clear_study_session(user_id)
            summary = session.get_summary()
            # Record analytics
            record_flashcard_completion(
                user_id=user_id,
                cards_reviewed=summary['reviewed'],
                remembered_count=summary['remembered']
            )
            summary_text = (
                f"📊 **Kết thúc flashcard**\n\n"
                f"🗂️ Tổng cards: {summary['total_cards']}\n"
                f"✅ Đã xem: {summary['reviewed']}\n"
                f"😊 Nhớ: {summary['remembered']}\n"
                f"😅 Chưa nhớ: {summary['forgotten']}\n"
                f"📈 Hoàn thành: {summary['completion_rate']:.1f}%"
            )
            await send_text_message(user_id, summary_text)
            return

        elif action == "flip":
            # Show back side
            await send_flashcard_back(user_id, session)
            return

        elif action == "skip":
            # Just skip to next without recording
            if session.next_card():
                await send_flashcard_front(user_id, session)
            else:
                clear_study_session(user_id)
                await send_text_message(user_id, "✅ Đã xem hết tất cả flashcard!")
            return

        elif action in {"remember", "forgot"}:
            # Record review
            remembered = (action == "remember")
            session.record_review(remembered)  # We don't need the return value here

            # Save progress
            save_study_session(user_id, session.doc_id, "flashcard", session.to_dict())

            # Feedback
            fb = "✅ Bạn nhớ rồi! Tuyệt vời!" if remembered else "😅 Không sao, cần ôn lại sau nhé!"
            await send_text_message(user_id, fb)

            # Auto-advance to next card
            if session.next_card():
                await send_flashcard_front(user_id, session)
            else:
                clear_study_session(user_id)
                summary = session.get_summary()
                summary_text = (
                    f"🎉 **Hoàn thành flashcard!**\n\n"
                    f"🗂️ Tổng cards: {summary['total_cards']}\n"
                    f"✅ Nhớ: {summary['remembered']}\n"
                    f"😅 Chưa nhớ: {summary['forgotten']}\n"
                    f"📈 Tỷ lệ nhớ: {summary['completion_rate']:.1f}%"
                )
                await send_long_text_message(user_id, summary_text, [
                    {"title": "🗂️ Ôn lại", "type": "oa.query.show", "payload": "STUDY_START_FLASHCARD"},
                    {"title": "📊 Tiến độ", "type": "oa.query.show", "payload": "STUDY_PROGRESS"},
                    {"title": "🔙 Menu", "type": "oa.query.show", "payload": "MENU"},
                ])
            return

        elif action == "next":
            # Skip without recording
            if session.next_card():
                await send_flashcard_front(user_id, session)
            else:
                clear_study_session(user_id)
                await send_text_message(user_id, "✅ Đã xem hết flashcard!")
            return

    except Exception as e:
        logger.error(f"Handle flashcard action error: {e}")
        await send_text_message(user_id, "❌ Lỗi xử lý. Vui lòng thử lại!")


def get_active_doc_id(user_id: str) -> str | None:
    """Helper lấy active doc ID."""
    doc = get_active_doc(user_id)
    if doc:
        return doc.get("id") if isinstance(doc, dict) else doc
    return None


async def start_study_session_by_mode(user_id: str, mode: str, doc_text: str):
    """Router bắt đầu study session theo mode."""
    if mode == "quiz":
        await start_quiz_session(user_id, doc_text)
    elif mode == "flashcard":
        await start_flashcard_session(user_id, doc_text)
    else:
        await send_text_message(user_id, "⚠️ Chế độ học không được hỗ trợ.")


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════
# MINI APP API ENDPOINTS
# ═════════════════════════════════════════════════════════════

@app.post("/api/miniapp/auth")
async def miniapp_auth(request: Request):
    """Exchange Zalo access token for user_id."""
    try:
        body = await request.json()
        access_token = body.get("access_token", "")
        if not access_token:
            return JSONResponse(content={"error": "Missing access_token"}, status_code=400)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://graph.zalo.me/v2.0/me?access_token={access_token}&fields=id,name"
            )
            if resp.status_code != 200:
                return JSONResponse(content={"error": "Invalid access token"}, status_code=401)
            data = resp.json()
            user_id = data.get("id")
            if not user_id:
                return JSONResponse(content={"error": "Cannot get user_id"}, status_code=401)
            return JSONResponse(content={"user_id": user_id, "name": data.get("name", "")})
    except Exception as exc:
        logger.error("Miniapp auth error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.get("/api/miniapp/documents")
async def miniapp_get_documents(request: Request):
    """List documents for the authenticated user."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)
        docs = get_user_docs(user_id)
        result = []
        for d in docs:
            result.append({
                "id": d.get("id", d.get("doc_id", "")),
                "name": d.get("name", d.get("file_name", "Untitled")),
                "doc_type": d.get("doc_type", "pdf"),
                "timestamp": d.get("timestamp", d.get("created_at", 0)),
                "summary": d.get("summary", d.get("summary_text", "")),
            })
        return JSONResponse(content=result)
    except Exception as exc:
        logger.error("Miniapp get documents error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.get("/api/miniapp/documents/{doc_id}")
async def miniapp_get_document(request: Request, doc_id: str):
    """Get a single document by ID with full details."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        supabase = get_supabase_client()
        if supabase:
            result = supabase.table("documents").select("*").eq("id", doc_id).eq("user_id", user_id).single().execute()
            if not result.data:
                return JSONResponse(content={"error": "Document not found"}, status_code=404)

            doc = result.data
            return JSONResponse(content={
                "id": doc.get("id"),
                "name": doc.get("name"),
                "doc_type": doc.get("doc_type"),
                "timestamp": doc.get("timestamp"),
                "summary": doc.get("summary"),
                "text": doc.get("text"),
                "flashcards": doc.get("flashcards", []),
                "quiz_questions": doc.get("quiz_questions", []),
                "content": doc.get("content"),
            })

        # Memory fallback
        if user_id in _memory_documents and doc_id in _memory_documents[user_id]:
            doc = _memory_documents[user_id][doc_id]
            return JSONResponse(content={
                "id": doc_id,
                "name": doc.get("name"),
                "doc_type": doc.get("doc_type"),
                "timestamp": doc.get("timestamp"),
                "summary": doc.get("summary"),
                "text": doc.get("text"),
                "flashcards": doc.get("flashcards", []),
                "quiz_questions": doc.get("quiz_questions", []),
            })

        return JSONResponse(content={"error": "Document not found"}, status_code=404)
    except Exception as exc:
        logger.error("Miniapp get document error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/documents")
async def miniapp_upload_document(request: Request):
    """Upload and process a document for Mini App."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        # Parse multipart form data
        form = await request.form()
        file = form.get("file")
        if not file:
            return JSONResponse(content={"error": "Missing file"}, status_code=400)

        filename = file.filename or "document"
        file_type = get_file_type(filename)

        if file_type == "unknown":
            return JSONResponse(content={"error": "Chỉ hỗ trợ PDF, Word (.docx), hoặc ảnh."}, status_code=400)

        # Read file content
        content = await file.read()

        if len(content) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            return JSONResponse(content={"error": f"File quá lớn! Tối đa {config.MAX_FILE_SIZE_MB}MB."}, status_code=400)

        # Save temp file
        temp_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(config.TEMP_DIR, temp_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        try:
            # Extract text / summarize
            doc_text = ""
            if file_type == "image":
                structured = await summarize_image_structured(file_path)
                # Extract OCR text for RAG Q&A
                doc_text = await extract_ocr_text(file_path)
            else:
                text, _ft = await extract_text(file_path, config.MAX_PAGES)
                if not text and _ft == "pdf":
                    # OCR fallback for scanned/handwritten PDF
                    page_images = await convert_pdf_to_images(file_path, max_pages=10)
                    if not page_images:
                        return JSONResponse(content={"error": "Không thể đọc file PDF này (scan/ảnh)."}, status_code=400)
                    try:
                        structured = await summarize_pdf_images_structured(page_images)
                    finally:
                        for img_path in page_images:
                            try:
                                os.remove(img_path)
                            except OSError:
                                pass
                elif not text:
                    return JSONResponse(content={"error": "Không đọc được nội dung file này."}, status_code=400)
                else:
                    doc_text = text
                    structured = await summarize_text_structured(text)

            if structured.get("error"):
                return JSONResponse(content={"error": str(structured["error"])}, status_code=500)

            # Generate doc_id
            doc_id = str(uuid.uuid4())

            # Create a nice string summary
            overview = structured.get("overview", "")
            points = structured.get("points", [])
            summary_str = overview
            if points:
                summary_str += "\n\nCác ý chính:\n" + "\n".join([f"• {p.get('title', '')}: {p.get('detail', '')}" for p in points])

            # Save document to DB (including flashcards and quiz)
            save_document(
                user_id=user_id,
                doc_id=doc_id,
                name=filename,
                text=doc_text or "[File không có text content]",
                summary=summary_str,
                doc_type=file_type,
                flashcards=structured.get("flashcards", []),
                quiz_questions=structured.get("quiz", [])
            )

            # 💰 CHARGE COINS for file processing (unless first-time free?)
            # Check if user has free quota first
            can_process_free = check_study_mode_limit(user_id)
            if not can_process_free:
                # User exceeded free limit, charge coins
                success = await spend_coins(user_id, FILE_PROCESS_COST, 'file_process', {'doc_id': doc_id})
                if not success:
                    # Insufficient coins - delete document and return error
                    delete_document_by_id(user_id, doc_id)
                    return JSONResponse(content={
                        "error": "Insufficient coins. Please top up!",
                        "code": "INSUFFICIENT_COINS",
                        "required": FILE_PROCESS_COST
                    }, status_code=402)

            # Save original text temporarily for Q&A (24h TTL)
            if doc_text:
                save_document_text_temp(user_id, doc_id, doc_text)

            # 📝 Generate quiz questions from document (if not already present)
            quiz_questions = structured.get("quiz", [])
            is_education = structured.get("document_type") == "education"
            
            # Chỉ generate thêm quiz nếu đây là tài liệu giáo dục mà prompt chính bị sót
            if not quiz_questions and doc_text and len(doc_text) > 100 and is_education:
                try:
                    from prompts.study_prompts import GENERATE_QUIZ_PROMPT
                    quiz_prompt = GENERATE_QUIZ_PROMPT.format(document_text=doc_text[:8000])
                    quiz_json_str = await _call_with_smart_routing(
                        quiz_prompt,
                        text_length=len(doc_text),
                        max_tokens=8192,
                        response_json=True,
                        force_gemini=False,
                    )
                    quiz_data = json.loads(quiz_json_str)
                    quiz_questions = quiz_data.get("questions", [])

                    # Update document with quiz questions
                    if supabase:
                        supabase.table("documents").update({
                            "quiz_questions": quiz_questions
                        }).eq("id", doc_id).eq("user_id", user_id).execute()

                    logger.info("✅ Quiz generated for doc %s: %s questions", doc_id[:8], len(quiz_questions))
                except Exception as quiz_err:
                    logger.warning("Quiz generation failed for doc %s: %s", doc_id[:8], quiz_err)
                    quiz_questions = []

            logger.info("✅ Miniapp upload success: user=%s, doc=%s, type=%s, flashcards=%s, quiz=%s",
                        user_id[:8], doc_id[:8], file_type,
                        len(structured.get("flashcards", [])), len(quiz_questions))

            return JSONResponse(content={
                "id": doc_id,
                "name": filename,
                "doc_type": file_type,
                "timestamp": time.time(),
                "summary": summary_str,
                "flashcard_count": len(structured.get("flashcards", [])),
                "quiz_count": len(quiz_questions),
                "quiz": quiz_questions,  # Return quiz questions to frontend
            }, status_code=201)

        finally:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    except Exception as exc:
        logger.error("Miniapp upload document error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/chat/ask")
async def miniapp_chat_ask(request: Request):
    """RAG-based Q&A endpoint cho Mini App."""
    try:
        body = await request.json()
        doc_id = body.get("document_id", "")
        question = body.get("question", "")
        user_id = body.get("user_id", "") or request.headers.get("X-User-Id", "")

        if not doc_id or not question or not user_id:
            return JSONResponse(
                content={"error": "Missing document_id, question, or user_id"},
                status_code=400
            )

        # Kiểm tra Q&A limit per document
        qa_count = get_qa_count(user_id, doc_id)
        if qa_count >= QA_LIMIT_PER_DOC:
            return JSONResponse(content={
                "error": "Đã hết lượt hỏi cho tài liệu này (tối đa 5 câu). Gửi lại file để mở phiên mới.",
                "code": "QA_LIMIT_EXCEEDED",
                "limit": QA_LIMIT_PER_DOC
            }, status_code=429)

        # Kiểm tra daily quota
        if not check_rate_limit(user_id):
            return JSONResponse(content={
                "error": "Đã hết lượt hỏi hôm nay. Vui lòng thử lại sau.",
                "code": "DAILY_LIMIT_EXCEEDED",
                "limit": config.FREE_DAILY_LIMIT
            }, status_code=429)

        # Gọi RAG pipeline
        logger.info("RAG Q&A: user=%s, doc=%s, question=%s", user_id[:8], doc_id[:8], question[:50])
        result = await rag_qa_pipeline(user_id, doc_id, question, top_k=5)

        if "error" in result:
            error_msg = result["error"]
            # Document not found/expired → 404
            if "not found" in error_msg.lower() or "expired" in error_msg.lower():
                status_code = 404
            else:
                status_code = 500
            return JSONResponse(content={"error": error_msg}, status_code=status_code)

        # Increment counters
        increment_qa_count(user_id, doc_id)
        increment_usage(user_id)  # Daily quota

        return JSONResponse(content={
            "answer": result["answer"],
            "sources": result["sources"]
        })

    except Exception as exc:
        logger.error("Miniapp chat ask error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


@app.get("/api/miniapp/documents/{doc_id}/flashcards")
async def miniapp_get_flashcards(doc_id: str, request: Request):
    """Get flashcards for a document."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        # Query flashcards from documents table
        if supabase:
            result = supabase.table("documents").select("flashcards").eq("id", doc_id).eq("user_id", user_id).execute()
            if not result.data:
                return JSONResponse(content=[], status_code=200)
            flashcards = result.data[0].get("flashcards") or []
            return JSONResponse(content=flashcards)

        # Memory fallback
        if user_id in _memory_documents and doc_id in _memory_documents[user_id]:
            return JSONResponse(content=_memory_documents[user_id][doc_id].get("flashcards") or [])

        return JSONResponse(content=[], status_code=200)
    except Exception as exc:
        logger.error("Miniapp get flashcards error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.get("/api/miniapp/documents/{doc_id}/quiz")
async def miniapp_get_quiz(doc_id: str, request: Request):
    """Get quiz questions for a document."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        # Query quiz questions from documents table
        if supabase:
            result = supabase.table("documents").select("quiz_questions").eq("id", doc_id).eq("user_id", user_id).execute()
            if not result.data:
                return JSONResponse(content=[], status_code=200)
            quiz_questions = result.data[0].get("quiz_questions") or []
            return JSONResponse(content=quiz_questions)

        # Memory fallback
        if user_id in _memory_documents and doc_id in _memory_documents[user_id]:
            return JSONResponse(content=_memory_documents[user_id][doc_id].get("quiz_questions") or [])

        return JSONResponse(content=[], status_code=200)
    except Exception as exc:
        logger.error("Miniapp get quiz error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/quiz/start")
async def miniapp_quiz_start(request: Request):
    """Start a quiz session for Mini App."""
    try:
        body = await request.json()
        doc_id = body.get("doc_id", "")
        user_id = body.get("user_id", "") or request.headers.get("X-User-Id", "")
        if not doc_id or not user_id:
            return JSONResponse(content={"error": "Missing doc_id or user_id"}, status_code=400)
        # Check if DB already has questions
        questions = []
        if supabase:
            res = supabase.table("documents").select("quiz_questions").eq("id", doc_id).eq("user_id", user_id).execute()
            if res.data and res.data[0].get("quiz_questions"):
                questions = res.data[0]["quiz_questions"]

        if not questions:
            # Generate new questions if none exist
            doc_text = get_document_text_temp(user_id, doc_id)
            if not doc_text:
                return JSONResponse(content={"error": "Document not found or expired"}, status_code=404)
            prompt = GENERATE_QUIZ_PROMPT.format(document_text=doc_text[:8000])
            quiz_json_str = await _call_with_smart_routing(
                prompt, text_length=len(doc_text), max_tokens=8192, response_json=True
            )
            quiz_data = json.loads(quiz_json_str)
            questions = quiz_data.get("questions", [])
            if not questions:
                return JSONResponse(content={"error": "Cannot generate quiz"}, status_code=500)
            
            # Save to DB for future use
            if supabase:
                supabase.table("documents").update({"quiz_questions": questions}).eq("id", doc_id).eq("user_id", user_id).execute()
        session = QuizSession(questions=questions, doc_id=doc_id)
        session.start()
        save_study_session(user_id, doc_id, "quiz", session.to_dict())
        first_q = session.get_current_question()
        return JSONResponse(content={
            "session_id": session.session_id,
            "doc_id": doc_id,
            "current_idx": session.current_idx,
            "score": session.score,
            "total": session.total_questions,
            "question": {
                "id": first_q["id"],
                "question": first_q["question"],
                "options": [o["label"] for o in first_q["options"]],
                "correct": next((i for i, o in enumerate(first_q["options"]) if o.get("isCorrect")), 0),
                "explanation": first_q.get("explanation", ""),
                "difficulty": first_q.get("difficulty", "medium"),
            },
        })
    except Exception as exc:
        logger.error("Miniapp quiz start error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/quiz/answer")
async def miniapp_quiz_answer(request: Request):
    """Submit a quiz answer from Mini App."""
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        answer = body.get("answer", "")
        user_id = body.get("user_id", "") or request.headers.get("X-User-Id", "")
        if not session_id or not answer:
            return JSONResponse(content={"error": "Missing session_id or answer"}, status_code=400)
        session_record = load_study_session(user_id)
        if not session_record or session_record["session_type"] != "quiz":
            return JSONResponse(content={"error": "No active quiz session"}, status_code=404)
        session = QuizSession.from_dict(session_record["data"])
        result = session.process_answer(answer)
        save_study_session(user_id, session.doc_id, "quiz", session.to_dict())
        response = {
            "is_correct": result["is_correct"],
            "correct_answer": result["correct_answer"],
            "explanation": result["explanation"],
            "is_last": result["is_last"],
            "next_action": result["next_action"],
            "feedback_text": result["feedback_text"],
        }
        if not result["is_last"]:
            q = session.get_current_question()
            if q:
                response["next_question"] = {
                    "id": q["id"],
                    "question": q["question"],
                    "options": [o["label"] for o in q["options"]],
                    "correct": next((i for i, o in enumerate(q["options"]) if o.get("isCorrect")), 0),
                    "explanation": q.get("explanation", ""),
                    "difficulty": q.get("difficulty", "medium"),
                }
        if result["is_last"]:
            clear_study_session(user_id)
            final = session.get_final_score()
            record_quiz_completion(user_id, final["correct"], final["total"], final.get("time_seconds", 0))

            # 🎁 AUTO-REWARD: Quiz completion (>=70% correct)
            reward_amount = await reward_quiz_complete(user_id, final["correct"], final["total"])
            if reward_amount > 0:
                logger.info("🎉 Quiz reward: user %s earned %s coins (score: %s/%s)",
                            user_id[:8], reward_amount, final["correct"], final["total"])

            response["final_score"] = final
        return JSONResponse(content=response)
    except Exception as exc:
        logger.error("Miniapp quiz answer error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/flashcard/start")
async def miniapp_flashcard_start(request: Request):
    """Start a flashcard session for Mini App."""
    try:
        body = await request.json()
        doc_id = body.get("doc_id", "")
        user_id = body.get("user_id", "") or request.headers.get("X-User-Id", "")
        if not doc_id or not user_id:
            return JSONResponse(content={"error": "Missing doc_id or user_id"}, status_code=400)
        # Check if DB already has flashcards
        flashcards = []
        if supabase:
            res = supabase.table("documents").select("flashcards").eq("id", doc_id).eq("user_id", user_id).execute()
            if res.data and res.data[0].get("flashcards"):
                flashcards = res.data[0]["flashcards"]

        if not flashcards:
            doc_text = get_document_text_temp(user_id, doc_id)
            if not doc_text:
                return JSONResponse(content={"error": "Document not found or expired"}, status_code=404)
            prompt = GENERATE_FLASHCARD_PROMPT.format(document_text=doc_text[:8000])
            flashcard_json_str = await _call_with_smart_routing(
                prompt, text_length=len(doc_text), max_tokens=8192, response_json=True
            )
            flashcard_data = json.loads(flashcard_json_str)
            flashcards = flashcard_data.get("flashcards", [])
            if not flashcards:
                return JSONResponse(content={"error": "Cannot generate flashcards"}, status_code=500)
            
            # Save to DB for future use
            if supabase:
                supabase.table("documents").update({"flashcards": flashcards}).eq("id", doc_id).eq("user_id", user_id).execute()

        session = FlashcardSession(flashcards=flashcards, doc_id=doc_id)
        save_study_session(user_id, doc_id, "flashcard", session.to_dict())
        card = session.get_current_card()
        return JSONResponse(content={
            "session_id": session.session_id,
            "doc_id": doc_id,
            "current_idx": session.current_idx,
            "total": session.total_cards,
            "card": {"id": f"{doc_id}_{session.current_idx}", "front": card["front"], "back": card["back"]},
        })
    except Exception as exc:
        logger.error("Miniapp flashcard start error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/flashcard/review")
async def miniapp_flashcard_review(request: Request):
    """Review a flashcard from Mini App."""
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        remembered = body.get("remembered", False)
        user_id = body.get("user_id", "") or request.headers.get("X-User-Id", "")
        session_record = load_study_session(user_id)
        if not session_record or session_record["session_type"] != "flashcard":
            return JSONResponse(content={"error": "No active flashcard session"}, status_code=404)
        session = FlashcardSession.from_dict(session_record["data"])
        session.record_review(remembered)
        save_study_session(user_id, session.doc_id, "flashcard", session.to_dict())
        response = {"is_done": False}
        if session.next_card():
            card = session.get_current_card()
            response["next_card"] = {"id": f"{session.doc_id}_{session.current_idx}", "front": card["front"], "back": card["back"]}
        else:
            response["is_done"] = True
            response["summary"] = session.get_summary()
            clear_study_session(user_id)
            record_flashcard_completion(user_id, response["summary"]["reviewed"], response["summary"]["remembered"])

            # 🎁 AUTO-REWARD: Flashcard completion (small reward per session)
            # Give 10 coins for completing a flashcard session (any size)
            reward_amount = await add_coins(user_id, 10, 'flashcard_complete', {
                'reviewed': response["summary"]["reviewed"],
                'remembered': response["summary"]["remembered"]
            })
            logger.info("🎉 Flashcard reward: user %s earned %s coins (reviewed: %s)",
                        user_id[:8], reward_amount, response["summary"]["reviewed"])

        return JSONResponse(content=response)
    except Exception as exc:
        logger.error("Miniapp flashcard review error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.get("/api/miniapp/documents/{doc_id}/progress")
async def miniapp_get_progress(doc_id: str, request: Request):
    """Get learning progress for a document."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)
        return JSONResponse(content={
            "summary_done": True, "flashcard_done": 0, "flashcard_total": 0,
            "quiz_done": 0, "quiz_total": 0, "overall_percent": 0,
        })
    except Exception as exc:
        logger.error("Miniapp progress error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.get("/api/miniapp/coin/balance")
async def miniapp_coin_balance(request: Request):
    """Get user's coin balance."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)
        balance = await get_coin_balance(user_id)
        return JSONResponse(content={"balance": balance, "today_usage": 0, "study_sessions_today": 0})
    except Exception as exc:
        logger.error("Miniapp coin balance error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/coin/earn")
async def miniapp_coin_earn(request: Request):
    """Earn coins (admin/reward only)."""
    try:
        body = await request.json()
        user_id = body.get("user_id") or request.headers.get("X-User-Id", "")
        amount = int(body.get("amount", 0))
        reason = body.get("reason", "reward")
        metadata = body.get("metadata", {})

        if not user_id or amount <= 0:
            return JSONResponse(content={"error": "Invalid request"}, status_code=400)

        new_balance = await add_coins(user_id, amount, reason, metadata)
        return JSONResponse(content={"success": True, "new_balance": new_balance})
    except Exception as exc:
        logger.error("Miniapp coin earn error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/coin/spend")
async def miniapp_coin_spend(request: Request):
    """Spend coins (for purchases)."""
    try:
        body = await request.json()
        user_id = body.get("user_id") or request.headers.get("X-User-Id", "")
        amount = int(body.get("amount", 0))
        reason = body.get("reason", "spend")
        metadata = body.get("metadata", {})

        if not user_id or amount <= 0:
            return JSONResponse(content={"error": "Invalid request"}, status_code=400)

        success = await spend_coins(user_id, amount, reason, metadata)
        if success:
            balance = await get_coin_balance(user_id)
            return JSONResponse(content={"success": True, "new_balance": balance})
        else:
            return JSONResponse(content={"error": "Insufficient coins", "code": "INSUFFICIENT_FUNDS"}, status_code=400)
    except Exception as exc:
        logger.error("Miniapp coin spend error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/share")
async def miniapp_share(request: Request):
    """Record a share action and reward user with coins."""
    try:
        body = await request.json()
        user_id = body.get("user_id") or request.headers.get("X-User-Id", "")
        share_type = body.get("type", "quiz_result")  # quiz_result, flashcard, document

        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        # Award coins for sharing (anti-spam: one reward per share action)
        reward_amount = await reward_share(user_id)
        logger.info("🎉 Share reward: user %s earned %s coins (type: %s)",
                    user_id[:8], reward_amount, share_type)

        return JSONResponse(content={"success": True, "coins_earned": reward_amount})
    except Exception as exc:
        logger.error("Miniapp share error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.get("/api/miniapp/coin/history")
async def miniapp_coin_history(request: Request):
    """Get coin transaction history."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        limit = int(request.query_params.get("limit", 20))
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        history = await get_transaction_history(user_id, limit)
        return JSONResponse(content=history)
    except Exception as exc:
        logger.error("Miniapp coin history error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/zalopay/create")
async def miniapp_zalopay_create(request: Request):
    """Create ZaloPay order for coin top-up."""
    try:
        body = await request.json()
        user_id = body.get("user_id") or request.headers.get("X-User-Id", "")
        package_id = body.get("package_id", "")

        if not user_id or not package_id:
            return JSONResponse(content={"error": "Missing user_id or package_id"}, status_code=400)

        result = await create_zalopay_order(user_id, package_id, "https://zalo.me/your_oa_id")
        if "error" in result:
            return JSONResponse(content=result, status_code=400)
        return JSONResponse(content=result)
    except Exception as exc:
        logger.error("ZaloPay create error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/zalopay/callback")
async def miniapp_zalopay_callback(request: Request):
    """Handle ZaloPay payment callback."""
    try:
        result = await verify_zalopay_callback(request)
        if "error" in result:
            return JSONResponse(content=result, status_code=400)
        return JSONResponse(content=result)
    except Exception as exc:
        logger.error("ZaloPay callback error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.delete("/api/miniapp/documents/{doc_id}")
async def miniapp_delete_document(doc_id: str, request: Request):
    """Delete a document."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)
        delete_document_by_id(user_id, doc_id)
        return JSONResponse(content={"status": "ok"})
    except Exception as exc:
        logger.error("Miniapp delete document error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.get("/api/miniapp/streak")
async def miniapp_get_streak(request: Request):
    """Get user's learning streak data."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        # Try to get streak from Supabase
        current_streak = 0
        longest_streak = 0
        streak_maintained = False

        if supabase:
            try:
                result = supabase.table("user_streaks").select("*").eq("user_id", user_id).execute()
                if result.data and len(result.data) > 0:
                    streak_data = result.data[0]
                    current_streak = streak_data.get("current_streak", 0)
                    longest_streak = streak_data.get("longest_streak", 0)
                    last_activity = streak_data.get("last_activity_date", "")
                    today = datetime.now().strftime("%Y-%m-%d")
                    streak_maintained = last_activity == today
            except Exception as e:
                logger.warning("Streak DB error: %s, using defaults", e)

        return JSONResponse(content={
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "streak_maintained": streak_maintained,
        })
    except Exception as exc:
        logger.error("Miniapp streak error: %s", exc)
        return JSONResponse(content={"current_streak": 0, "longest_streak": 0, "streak_maintained": False})


@app.post("/api/miniapp/documents/{doc_id}/rename")
async def miniapp_rename_document(doc_id: str, request: Request):
    """Rename a document."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        body = await request.json()
        new_name = body.get("name", "").strip()
        if not new_name:
            return JSONResponse(content={"error": "Missing name"}, status_code=400)

        if supabase:
            supabase.table("documents").update({"name": new_name}).eq("id", doc_id).eq("user_id", user_id).execute()
        elif user_id in _memory_documents and doc_id in _memory_documents[user_id]:
            _memory_documents[user_id][doc_id]["name"] = new_name

        return JSONResponse(content={"status": "ok", "name": new_name})
    except Exception as exc:
        logger.error("Miniapp rename document error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.get("/api/miniapp/quiz/{session_id}/result")
async def miniapp_quiz_result(session_id: str, request: Request):
    """Get quiz result for a session."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        # Try to load session from memory or DB
        session_record = load_study_session(user_id)
        if session_record and session_record.get("session_type") == "quiz":
            session = QuizSession.from_dict(session_record["data"])
            final = session.get_final_score()
            return JSONResponse(content={
                "correct": final["correct"],
                "total": final["total"],
                "percentage": round((final["correct"] / max(final["total"], 1)) * 100),
                "grade": "Xuất sắc" if final["correct"] / max(final["total"], 1) >= 0.8 else "Khá" if final["correct"] / max(final["total"], 1) >= 0.5 else "Cần cải thiện",
                "time_seconds": final.get("time_seconds", 0),
            })

        return JSONResponse(content={"error": "Session not found"}, status_code=404)
    except Exception as exc:
        logger.error("Miniapp quiz result error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.get("/api/miniapp/quiz/{session_id}/review")
async def miniapp_quiz_review(session_id: str, request: Request):
    """Get quiz review with all questions and answers."""
    try:
        user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id", "")
        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        session_record = load_study_session(user_id)
        if session_record and session_record.get("session_type") == "quiz":
            session = QuizSession.from_dict(session_record["data"])
            review = session.get_review()
            return JSONResponse(content=review)

        # If no active session, return basic info
        return JSONResponse(content={
            "total": 0, "correct": 0, "wrong": 0, "questions": []
        })
    except Exception as exc:
        logger.error("Miniapp quiz review error: %s", exc)
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@app.post("/api/miniapp/solve-problem")
async def miniapp_solve_problem(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Upload image of a problem → AI generates step-by-step solution.

    Process:
    1. Gemini Vision OCR extracts text from image
    2. DeepSeek (via Gemini) generates detailed solution with steps

    Returns JSON:
    {
      "question": "tóm tắt đề bài",
      "steps": ["bước 1", "bước 2", ...],
      "answer": "đáp án cuối cùng"
    }
    """
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        return JSONResponse(
            content={"error": "Chỉ hỗ trợ ảnh JPG, PNG, WebP"},
            status_code=400
        )

    # Save uploaded file temporarily
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from services.solve_service import solve_problem_image
        result = await solve_problem_image(tmp_path, user_id)
        return JSONResponse(content=result)
    except ValueError as e:
        logger.warning("Solve problem validation error for user %s: %s", user_id, e)
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Solve problem error for user %s: %s", user_id, e, exc_info=True)
        return JSONResponse(content={"error": "Không thể giải bài. Vui lòng thử lại."}, status_code=500)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/miniapp/generate-quiz-from-solution")
async def generate_quiz_from_solution(request: Request):
    """
    Generate 5 quiz questions from a solved problem (question + steps + answer).

    Request JSON:
    {
      "question": "Đề bài...",
      "steps": ["bước 1", ...],
      "answer": "đáp án"
    }

    Returns (using GENERATE_QUIZ_PROMPT):
    {
      "questions": [
        {
          "question": "Câu hỏi?",
          "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
          "correct": 0,
          "explanation": "Giải thích",
          "difficulty": "easy|medium|hard"
        }
      ]
    }
    """
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

    try:
        body = await request.json()
        question = body.get("question", "").strip()
        steps = body.get("steps", [])
        answer = body.get("answer", "").strip()

        if not question or not steps or not answer:
            return JSONResponse(
                content={"error": "Thiếu question/steps/answer"},
                status_code=400
            )

        # Build context from solution
        context = f"ĐỀ BÀI:\n{question}\n\nLỜI GIẢI:\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))

        # Use existing quiz generation prompt
        from prompts.study_prompts import GENERATE_QUIZ_PROMPT
        prompt = GENERATE_QUIZ_PROMPT.format(document_text=context)

        # Call DeepSeek/Gemini with smart routing
        result = await _call_with_smart_routing(
            [prompt],
            text_length=0,
            max_tokens=2000,
            response_json=True,
        )

        # Parse JSON
        try:
            quiz_data = json.loads(result)
        except json.JSONDecodeError:
            logger.error("Invalid quiz JSON from AI for user %s: %s", user_id, result[:200])
            return JSONResponse(
                content={"error": "Không thể tạo quiz. Vui lòng thử lại."},
                status_code=500
            )

        # Validate structure
        if "questions" not in quiz_data or not isinstance(quiz_data["questions"], list):
            return JSONResponse(
                content={"error": "Invalid quiz format"},
                status_code=500
            )

        # Limit to 5 questions
        quiz_data["questions"] = quiz_data["questions"][:5]

        logger.info(
            "Quiz generated from solution for user %s: %d questions",
            user_id, len(quiz_data["questions"])
        )

        return JSONResponse(content=quiz_data)

    except json.JSONDecodeError:
        return JSONResponse(
            content={"error": "Invalid request JSON"},
            status_code=400
        )
    except Exception as e:
        logger.error("Generate quiz from solution error for user %s: %s", user_id, e, exc_info=True)
        return JSONResponse(
            content={"error": "Không thể tạo quiz. Vui lòng thử lại."},
            status_code=500
        )




# Include shared quiz router if available
if shared_quiz_router:
    app.include_router(shared_quiz_router)

# @app.post("/api/miniapp/chat/ask")
# async def miniapp_chat_ask(request: Request):
#     """Chat với tài liệu sử dụng RAG - Tạm disable."""
#     return JSONResponse(content={"answer": "RAG chưa sẵn sàng", "sources": []}, status_code=503)


if __name__ == "__main__":
    try:
        logger.info("🚀 Starting server on %s:%s", config.HOST, config.PORT)
        uvicorn.run(
            "zalo_webhook:app",
            host=config.HOST,
            port=config.PORT,
            reload=False,
            log_level="info"
        )
    except Exception as e:
        logger.error("Failed to start server: %s", e, exc_info=True)
        raise

