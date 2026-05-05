"""Zalo OA Broadcast Service — Re-engagement via Zalo OA messages."""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Streak thresholds for reminders
STREAK_REMINDER_DAYS = [2, 3, 5, 7, 14, 30]


async def check_streak_reminders(supabase, zalo_access_token: str) -> int:
    """Kiểm tra user vắng mặt và gửi tin nhắn nhắc nhở."""
    try:
        # Get users with active streaks who haven't been active recently
        one_day_ago = time.time() - 24 * 3600
        seven_days_ago = time.time() - 7 * 24 * 3600

        # Get user_state with streak > 0 and last_active < now - 2 days
        result = supabase.table('user_state').select('user_id, streak_count, last_active').lt('last_active', one_day_ago).gt('streak_count', 0).execute()

        if not result.data:
            return 0

        sent_count = 0
        for user in result.data:
            user_id = user['user_id']
            streak = user['streak_count']
            last_active = user.get('last_active', 0)

            # Check if should send reminder (2 days inactive)
            if last_active and (time.time() - last_active) > 2 * 24 * 3600:
                message = f"🔥 Streak {streak} ngày của bạn sắp mất! Quay lại ngay để giữ nhé!"
                success = await send_zalo_message(zalo_access_token, user_id, message)
                if success:
                    sent_count += 1
                    logger.info("✅ Sent streak reminder to user %s", user_id[:8])

        return sent_count
    except Exception as e:
        logger.error("Check streak reminders error: %s", e)
        return 0


async def check_flashcard_reminders(supabase, zalo_access_token: str) -> int:
    """Nhắc user lật Flashcard chưa xem."""
    try:
        # Get users with active flashcard sessions
        result = supabase.table('study_sessions').select('user_id, state').eq('mode', 'flashcard').execute()

        if not result.data:
            return 0

        sent_count = 0
        for session in result.data:
            user_id = session['user_id']
            state = session.get('state', {})
            cards = state.get('cards', [])
            current_idx = state.get('current_idx', 0)

            if current_idx < len(cards):
                message = f"🃏 Bạn còn {len(cards) - current_idx} thẻ Flashcard chưa lật. Vào học ngay!"
                success = await send_zalo_message(zalo_access_token, user_id, message)
                if success:
                    sent_count += 1

        return sent_count
    except Exception as e:
        logger.error("Check flashcard reminders error: %s", e)
        return 0


async def send_milestone_notification(zalo_access_token: str, user_id: str, milestone: str, coin_reward: int):
    """Gửi thông báo đạt cột mốc (Streak 7, 30...)."""
    message = f"🎉 Chúc mừng! Bạn đã đạt {milestone}. Bạn nhận được {coin_reward} Coin!"
    return await send_zalo_message(zalo_access_token, user_id, message)


async def send_zalo_message(access_token: str, user_id: str, message: str) -> bool:
    """Gửi tin nhắn Zalo OA đến user."""
    try:
        import httpx
        url = "https://openapi.zalo.me/v3.0/oa/message"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"user_id": user_id},
            "message": {"text": message},
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                return True
            else:
                logger.warning("Zalo message failed: %s - %s", resp.status_code, resp.text[:200])
                return False
    except Exception as e:
        logger.error("Send Zalo message error: %s", e)
        return False


async def broadcast_daily_summary(supabase, zalo_access_token: str) -> dict:
    """Gửi báo cáo hàng ngày cho admin (optional)."""
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Count today's activity
        usage_result = supabase.table('user_usage').select('count').eq('date', today).execute()
        active_users = usage_result.data[0]['count'] if usage_result.data else 0

        # Count new documents today
        docs_result = supabase.table('documents').select('count').gte('timestamp', time.time() - 24*3600).execute()
        new_docs = docs_result.data[0]['count'] if docs_result.data else 0

        summary = {
            "date": today,
            "active_users": active_users,
            "new_documents": new_docs,
        }

        logger.info("📊 Daily summary: %s", summary)
        return summary
    except Exception as e:
        logger.error("Broadcast daily summary error: %s", e)
        return {}
