"""Deadline Service — Auto-extract, store, and remind deadlines from documents.

Flow:
  1. AI summarizer trả về `deadlines` array trong structured result
  2. Webhook gọi `save_deadlines_from_summary()` sau khi tóm tắt thành công
  3. Background scheduler chạy mỗi giờ, check deadlines sắp đến
  4. Gửi nhắc nhở qua Zalo OA CS message (free, trong cửa sổ 7 ngày)

Nhắc nhở sẽ gửi:
  - Trước 3 ngày (nhắc sớm)
  - Trước 1 ngày (nhắc gấp)
  - Đúng ngày (nhắc cuối cùng)

Lưu ý Zalo OA:
  - CS Message chỉ gửi được nếu user tương tác trong 7 ngày gần nhất
  - Nếu user không tương tác, deadline được đánh dấu "pending_notify"
  - Khi user quay lại tương tác → gửi nhắc nhở tích lũy
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# IN-MEMORY STORAGE (fallback khi chưa có Supabase table)
# ═══════════════════════════════════════════════════════════════

# Key: user_id -> list of deadline dicts
_memory_deadlines: dict[str, list[dict]] = {}

# Key: user_id -> timestamp of last interaction (for 7-day window check)
_user_last_interaction: dict[str, float] = {}

# Reminder states: deadline_key -> set of reminder types already sent
# deadline_key = f"{user_id}:{task}:{date}"
_sent_reminders: dict[str, set[str]] = {}

# Max deadlines per user (prevent spam)
MAX_DEADLINES_PER_USER = 50


# ═══════════════════════════════════════════════════════════════
# CORE METHODS
# ═══════════════════════════════════════════════════════════════

def update_user_interaction(user_id: str):
    """Ghi nhận user vừa tương tác — refresh cửa sổ 7 ngày."""
    _user_last_interaction[user_id] = time.time()


def is_user_reachable(user_id: str) -> bool:
    """Kiểm tra user có trong cửa sổ 7 ngày không (Zalo CS Message limit)."""
    last_ts = _user_last_interaction.get(user_id)
    if not last_ts:
        return False
    seven_days_ago = time.time() - (7 * 24 * 3600)
    return last_ts > seven_days_ago


def save_deadlines_from_summary(
    user_id: str,
    structured_summary: dict[str, Any],
    doc_title: str = "",
):
    """Trích xuất và lưu deadlines từ kết quả AI summarizer.
    
    Gọi hàm này sau khi summarize thành công, KHÔNG gọi thêm API nào.
    """
    deadlines = structured_summary.get("deadlines", [])
    if not deadlines:
        return 0

    doc_type = structured_summary.get("document_type", "general")
    saved_count = 0

    if user_id not in _memory_deadlines:
        _memory_deadlines[user_id] = []

    for dl in deadlines:
        task = dl.get("task", "").strip()
        date_str = dl.get("date", "").strip()
        assignee = dl.get("assignee", "").strip()
        note = dl.get("note", "").strip()

        if not task or not date_str:
            continue

        # Validate date format
        parsed_date = _parse_date(date_str)
        if not parsed_date:
            logger.warning("Invalid deadline date '%s', skipping", date_str)
            continue

        # Kiểm tra trùng lặp
        is_duplicate = any(
            d["task"].lower() == task.lower() and d["date"] == date_str
            for d in _memory_deadlines[user_id]
        )
        if is_duplicate:
            continue

        deadline_entry = {
            "task": task,
            "date": date_str,          # YYYY-MM-DD
            "assignee": assignee,
            "note": note,
            "doc_title": doc_title,
            "doc_type": doc_type,
            "created_at": time.strftime("%Y-%m-%d %H:%M"),
            "status": "active",        # active | done | expired
        }
        _memory_deadlines[user_id].append(deadline_entry)
        saved_count += 1
        logger.info("Deadline saved for user %s: '%s' @ %s", user_id, task, date_str)

    # Giới hạn số deadlines per user
    while len(_memory_deadlines[user_id]) > MAX_DEADLINES_PER_USER:
        _memory_deadlines[user_id].pop(0)

    return saved_count


def get_user_deadlines(user_id: str, include_expired: bool = False) -> list[dict]:
    """Lấy danh sách deadlines của user (mặc định chỉ lấy active)."""
    if user_id not in _memory_deadlines:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    result = []

    for dl in _memory_deadlines[user_id]:
        if dl["status"] == "done":
            continue
        if not include_expired and dl["date"] < today:
            dl["status"] = "expired"
            continue
        result.append(dl)

    # Sắp xếp theo ngày gần nhất trước
    result.sort(key=lambda x: x["date"])
    return result


def mark_deadline_done(user_id: str, task_keyword: str) -> bool:
    """Đánh dấu deadline đã hoàn thành bằng keyword."""
    if user_id not in _memory_deadlines:
        return False

    keyword = task_keyword.lower().strip()
    for dl in _memory_deadlines[user_id]:
        if keyword in dl["task"].lower() and dl["status"] == "active":
            dl["status"] = "done"
            logger.info("Deadline marked done: '%s' for user %s", dl["task"], user_id)
            return True
    return False


def get_upcoming_deadlines(user_id: str, days_ahead: int = 7) -> list[dict]:
    """Lấy deadlines trong N ngày tới."""
    today = datetime.now()
    cutoff = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    active = get_user_deadlines(user_id)
    return [dl for dl in active if today_str <= dl["date"] <= cutoff]


def get_all_users_with_deadlines() -> list[str]:
    """Lấy danh sách user_id có deadlines."""
    return list(_memory_deadlines.keys())


# ═══════════════════════════════════════════════════════════════
# REMINDER LOGIC
# ═══════════════════════════════════════════════════════════════

def get_deadlines_needing_reminder(user_id: str) -> list[tuple[dict, str]]:
    """Kiểm tra deadlines cần nhắc nhở.
    
    Returns list of (deadline_dict, reminder_type) tuples.
    reminder_type: "3day" | "1day" | "today"
    """
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    three_days_str = (today + timedelta(days=3)).strftime("%Y-%m-%d")

    results: list[tuple[dict, str]] = []
    active = get_user_deadlines(user_id)

    for dl in active:
        dl_key = f"{user_id}:{dl['task']}:{dl['date']}"
        sent = _sent_reminders.get(dl_key, set())

        if dl["date"] == today_str and "today" not in sent:
            results.append((dl, "today"))
        elif dl["date"] == tomorrow_str and "1day" not in sent:
            results.append((dl, "1day"))
        elif dl["date"] == three_days_str and "3day" not in sent:
            results.append((dl, "3day"))

    return results


def mark_reminder_sent(user_id: str, deadline: dict, reminder_type: str):
    """Đánh dấu đã gửi nhắc nhở cho deadline."""
    dl_key = f"{user_id}:{deadline['task']}:{deadline['date']}"
    if dl_key not in _sent_reminders:
        _sent_reminders[dl_key] = set()
    _sent_reminders[dl_key].add(reminder_type)


def get_pending_notifications(user_id: str) -> list[dict]:
    """Lấy các thông báo tích lũy khi user quay lại sau 7 ngày.
    
    Gọi hàm này khi user tương tác lại → gửi các nhắc nhở bị miss.
    """
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    active = get_user_deadlines(user_id)

    pending = []
    for dl in active:
        # Deadlines trong 3 ngày tới mà chưa nhắc
        dl_key = f"{user_id}:{dl['task']}:{dl['date']}"
        sent = _sent_reminders.get(dl_key, set())
        days_until = (_parse_date(dl["date"]) - today).days if _parse_date(dl["date"]) else -1

        if 0 <= days_until <= 3 and not sent:
            pending.append(dl)

    return pending


# ═══════════════════════════════════════════════════════════════
# MESSAGE FORMATTING
# ═══════════════════════════════════════════════════════════════

def format_reminder_message(deadline: dict, reminder_type: str) -> str:
    """Format tin nhắn nhắc nhở deadline."""
    task = deadline["task"]
    date = deadline["date"]
    assignee = deadline.get("assignee", "")
    doc_title = deadline.get("doc_title", "")
    note = deadline.get("note", "")

    if reminder_type == "today":
        urgency = "🔴 HÔM NAY"
        emoji = "⚡"
    elif reminder_type == "1day":
        urgency = "🟡 NGÀY MAI"
        emoji = "⏰"
    else:
        urgency = "🟢 Còn 3 ngày"
        emoji = "📋"

    lines = [
        f"{emoji} NHẮC DEADLINE {urgency}",
        f"━━━━━━━━━━━━━━━━━━",
        f"📌 {task}",
        f"📅 Hạn: {_format_date_vn(date)}",
    ]

    if assignee:
        lines.append(f"👤 Phụ trách: {assignee}")
    if doc_title:
        lines.append(f"📄 Từ tài liệu: {doc_title}")
    if note:
        lines.append(f"💡 Ghi chú: {note}")

    lines.append("")
    lines.append("👉 Nhắn 'XONG [keyword]' nếu đã hoàn thành.")

    return "\n".join(lines)


def format_deadline_list(deadlines: list[dict]) -> str:
    """Format danh sách deadlines cho lệnh DEADLINE / LỊCH."""
    if not deadlines:
        return (
            "📅 Bạn chưa có deadline nào.\n\n"
            "Gửi cho mình quyết định phân công, hợp đồng, hoặc lịch họp — "
            "mình sẽ tự trích xuất deadline và nhắc nhở bạn đúng hạn!"
        )

    today = datetime.now()
    lines = [
        "📅 DEADLINE CỦA BẠN",
        "━━━━━━━━━━━━━━━━━━",
    ]

    for i, dl in enumerate(deadlines, 1):
        parsed = _parse_date(dl["date"])
        if parsed:
            days_left = (parsed - today).days
            if days_left < 0:
                time_badge = "⚫ Đã qua"
            elif days_left == 0:
                time_badge = "🔴 Hôm nay!"
            elif days_left == 1:
                time_badge = "🟡 Ngày mai"
            elif days_left <= 3:
                time_badge = f"🟠 Còn {days_left} ngày"
            elif days_left <= 7:
                time_badge = f"🟢 Còn {days_left} ngày"
            else:
                time_badge = f"⚪ Còn {days_left} ngày"
        else:
            time_badge = "❓"

        assignee_part = f" — {dl['assignee']}" if dl.get("assignee") else ""
        lines.append(f"{i}. {time_badge} {_format_date_vn(dl['date'])}")
        lines.append(f"   📌 {dl['task']}{assignee_part}")

    lines.append("")
    lines.append(f"📊 Tổng: {len(deadlines)} deadline")
    lines.append("👉 Nhắn 'XONG [keyword]' để đánh dấu hoàn thành")

    return "\n".join(lines)


def format_deadline_saved_notice(count: int, deadlines: list[dict]) -> str:
    """Format thông báo đã lưu deadline (kèm vào cuối summary)."""
    if count == 0:
        return ""

    lines = [f"\n⏰ Phát hiện {count} deadline:"]
    for dl in deadlines[:5]:  # Chỉ hiện 5 deadline đầu
        assignee = f" ({dl['assignee']})" if dl.get("assignee") else ""
        lines.append(f"  • {_format_date_vn(dl['date'])}: {dl['task']}{assignee}")

    lines.append("✅ Đã lưu! Mình sẽ tự nhắc nhở trước khi đến hạn.")
    lines.append("📅 Nhắn 'DEADLINE' để xem tất cả.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# BACKGROUND SCHEDULER
# ═══════════════════════════════════════════════════════════════

_scheduler_running = False
_send_message_func = None  # Will be set by webhook module


def set_message_sender(func):
    """Inject hàm gửi tin nhắn Zalo từ webhook module.
    
    Tránh circular import: webhook import deadline_service,
    deadline_service cần gọi send_text_message từ webhook.
    """
    global _send_message_func
    _send_message_func = func
    logger.info("Deadline reminder message sender configured")


async def _run_reminder_check():
    """Kiểm tra và gửi nhắc nhở cho tất cả users."""
    if not _send_message_func:
        logger.warning("Message sender not configured, skipping reminder check")
        return

    all_users = get_all_users_with_deadlines()
    sent_count = 0

    for user_id in all_users:
        # Chỉ gửi nếu user còn trong cửa sổ 7 ngày
        if not is_user_reachable(user_id):
            continue

        reminders = get_deadlines_needing_reminder(user_id)
        for deadline, reminder_type in reminders:
            try:
                msg = format_reminder_message(deadline, reminder_type)
                await _send_message_func(user_id, msg)
                mark_reminder_sent(user_id, deadline, reminder_type)
                sent_count += 1
                # Rate limit: đợi 1s giữa các tin nhắn
                await asyncio.sleep(1)
            except Exception as exc:
                logger.error("Failed to send reminder to %s: %s", user_id, exc)

    if sent_count > 0:
        logger.info("Reminder check complete: sent %s reminders", sent_count)


async def start_reminder_scheduler():
    """Background scheduler — chạy mỗi giờ kiểm tra deadlines.
    
    Gọi trong FastAPI lifespan để chạy nền.
    """
    global _scheduler_running
    _scheduler_running = True
    logger.info("⏰ Deadline reminder scheduler started (interval: 1 hour)")

    while _scheduler_running:
        try:
            await _run_reminder_check()
        except Exception as exc:
            logger.error("Scheduler error: %s", exc, exc_info=True)

        # Chờ 1 giờ (3600s), check mỗi 60s để dừng nhanh khi shutdown
        for _ in range(60):
            if not _scheduler_running:
                break
            await asyncio.sleep(60)

    logger.info("Deadline reminder scheduler stopped")


def stop_reminder_scheduler():
    """Dừng scheduler khi server shutdown."""
    global _scheduler_running
    _scheduler_running = False


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _parse_date(date_str: str) -> datetime | None:
    """Parse date string (YYYY-MM-DD) thành datetime."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _format_date_vn(date_str: str) -> str:
    """Format YYYY-MM-DD → dd/mm/yyyy (format Việt Nam)."""
    parsed = _parse_date(date_str)
    if parsed:
        return parsed.strftime("%d/%m/%Y")
    return date_str
