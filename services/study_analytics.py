"""Study Mode Analytics — track completion, scores, retention with Supabase persistence."""

import logging
import time
from collections import defaultdict
from typing import Any
from datetime import datetime, timezone
from config import config
from services.db_service import get_supabase_client

logger = logging.getLogger(__name__)

# In-memory analytics store (TTL 7 days) - for fallback
_analytics: dict[str, dict] = {
    "quiz_scores": [],      # List of {"user_id": str, "score": int, "total": int, "percentage": float, "timestamp": float}
    "flashcard_reviews": [],  # List of {"user_id": str, "cards_reviewed": int, "remembered_pct": float, "timestamp": float}
    "sessions_started": 0,
    "sessions_completed": 0,
}

def record_quiz_completion(user_id: str | int, score: int, total: int, time_seconds: float = 0, shared_quiz_id: str | None = None, doc_id: str | None = None):
    """
    Log quiz completion with Supabase persistence.

    Args:
        user_id: User identifier
        score: Number of correct answers
        total: Total questions
        time_seconds: Time spent on quiz
        shared_quiz_id: UUID of shared quiz (if this is a public quiz)
        doc_id: Document ID (if this is a personal quiz)
    """
    entry = {
        "user_id": str(user_id),
        "score": score,
        "total": total,
        "percentage": (score / total * 100) if total > 0 else 0,
        "time_seconds": time_seconds,
        "timestamp": time.time(),
    }

    # Always save to in-memory (fallback)
    _analytics["quiz_scores"].append(entry)
    _analytics["sessions_completed"] += 1

    # PERSIST TO Supabase quiz_scores table
    supabase = get_supabase_client()
    if supabase:
        try:
            import uuid
            supabase.table("quiz_scores").insert({
                "id": str(uuid.uuid4()),
                "user_id": str(user_id),
                "doc_id": doc_id,
                "shared_quiz_id": shared_quiz_id,
                "quiz_id": hash(str(user_id) + str(time.time())),  # Simple hash for grouping
                "score": score,
                "total_questions": total,
                "percentage": entry["percentage"],
                "time_seconds": time_seconds,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            logger.info("Quiz score saved to Supabase: user=%s, score=%d/%d", user_id, score, total)
        except Exception as e:
            logger.warning("Failed to save quiz score to Supabase: %s", e)

    logger.info("Study analytics: quiz completed — user=%s, score=%d/%d (%.1f%%)",
                user_id, score, total, entry["percentage"])


def record_flashcard_completion(user_id: str | int, cards_reviewed: int, remembered_count: int, flashcard_data: list | None = None):
    """
    Log flashcard session completion with Supabase persistence.

    Args:
        user_id: User identifier
        cards_reviewed: Total cards reviewed
        remembered_count: Cards remembered correctly
        flashcard_data: List of flashcard progress data for SM-2 persistence
    """
    remembered_pct = (remembered_count / cards_reviewed * 100) if cards_reviewed > 0 else 0
    entry = {
        "user_id": str(user_id),
        "cards_reviewed": cards_reviewed,
        "remembered_count": remembered_count,
        "remembered_pct": remembered_pct,
        "timestamp": time.time(),
    }
    _analytics["flashcard_reviews"].append(entry)
    _analytics["sessions_completed"] += 1

    # PERSIST SM-2 progress to flashcard_progress table
    supabase = get_supabase_client()
    if supabase and flashcard_data:
        try:
            import uuid
            for card in flashcard_data:
                supabase.table("flashcard_progress").upsert({
                    "id": str(uuid.uuid4()),
                    "user_id": str(user_id),
                    "doc_id": card.get("doc_id"),
                    "card_hash": card.get("card_hash"),
                    "front": card.get("front"),
                    "back": card.get("back"),
                    "ease_factor": card.get("ease_factor", 2.5),
                    "interval": card.get("interval", 0),
                    "repetitions": card.get("repetitions", 0),
                    "last_reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "next_review_at": card.get("next_review_at"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
            logger.info("Flashcard progress saved to Supabase: user=%s, cards=%d", user_id, cards_reviewed)
        except Exception as e:
            logger.warning("Failed to save flashcard progress to Supabase: %s", e)

    logger.info("Study analytics: flashcard completed — user=%s, cards=%d, remembered=%.1f%%",
                user_id, cards_reviewed, remembered_pct)


def increment_sessions_started():
    _analytics["sessions_started"] += 1


def get_summary() -> dict[str, Any]:
    """Return aggregated analytics for admin/debug."""
    quiz_scores = _analytics["quiz_scores"]
    flash_reviews = _analytics["flashcard_reviews"]

    summary = {
        "sessions_started": _analytics["sessions_started"],
        "sessions_completed": _analytics["sessions_completed"],
    }

    if quiz_scores:
        avg_quiz_pct = sum(q["percentage"] for q in quiz_scores) / len(quiz_scores)
        summary["quiz"] = {
            "count": len(quiz_scores),
            "avg_score_pct": round(avg_quiz_pct, 1),
            "recent": quiz_scores[-5:],  # Last 5
        }

    if flash_reviews:
        avg_remembered = sum(f["remembered_pct"] for f in flash_reviews) / len(fash_reviews)
        summary["flashcard"] = {
            "count": len(flash_reviews),
            "avg_remembered_pct": round(avg_remembered, 1),
            "recent": flash_reviews[-5:],
        }

    return summary


def cleanup_old_data():
    """Remove entries older than 7 days to prevent memory bloat."""
    cutoff = time.time() - (7 * 24 * 3600)
    before_q = len(_analytics["quiz_scores"])
    before_f = len(_analytics["flashcard_reviews"])
    _analytics["quiz_scores"] = [q for q in _analytics["quiz_scores"] if q["timestamp"] > cutoff]
    _analytics["flashcard_reviews"] = [f for f in _analytics["flashcard_reviews"] if f["timestamp"] > cutoff]
    removed = (before_q - len(_analytics["quiz_scores"])) + (before_f - len(_analytics["flashcard_reviews"]))
    if removed:
        logger.info("Cleaned up %s old analytics entries", removed)