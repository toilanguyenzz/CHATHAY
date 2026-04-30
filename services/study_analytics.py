"""Study Mode Analytics — track completion, scores, retention."""

import logging
from collections import defaultdict
from typing import Any
from config import config

logger = logging.getLogger(__name__)

# In-memory analytics store (TTL 7 days)
_analytics: dict[str, dict] = {
    "quiz_scores": [],      # List of {"user_id": str, "score": int, "total": int, "percentage": float, "timestamp": float}
    "flashcard_reviews": [],  # List of {"user_id": str, "cards_reviewed": int, "remembered_pct": float, "timestamp": float}
    "sessions_started": 0,
    "sessions_completed": 0,
}

def record_quiz_completion(user_id: str | int, score: int, total: int, time_seconds: float = 0):
    """Log quiz completion."""
    entry = {
        "user_id": str(user_id),
        "score": score,
        "total": total,
        "percentage": (score / total * 100) if total > 0 else 0,
        "time_seconds": time_seconds,
        "timestamp": __import__("time").time(),
    }
    _analytics["quiz_scores"].append(entry)
    _analytics["sessions_completed"] += 1
    logger.info("Study analytics: quiz completed — user=%s, score=%d/%d (%.1f%%)",
                user_id, score, total, entry["percentage"])

def record_flashcard_completion(user_id: str | int, cards_reviewed: int, remembered_count: int):
    """Log flashcard session completion."""
    remembered_pct = (remembered_count / cards_reviewed * 100) if cards_reviewed > 0 else 0
    entry = {
        "user_id": str(user_id),
        "cards_reviewed": cards_reviewed,
        "remembered_count": remembered_count,
        "remembered_pct": remembered_pct,
        "timestamp": __import__("time").time(),
    }
    _analytics["flashcard_reviews"].append(entry)
    _analytics["sessions_completed"] += 1
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
        avg_remembered = sum(f["remembered_pct"] for f in flash_reviews) / len(flash_reviews)
        summary["flashcard"] = {
            "count": len(flash_reviews),
            "avg_remembered_pct": round(avg_remembered, 1),
            "recent": flash_reviews[-5:],
        }

    return summary

def cleanup_old_data():
    """Remove entries older than 7 days to prevent memory bloat."""
    import time
    cutoff = time.time() - (7 * 24 * 3600)
    before_q = len(_analytics["quiz_scores"])
    before_f = len(_analytics["flashcard_reviews"])
    _analytics["quiz_scores"] = [q for q in _analytics["quiz_scores"] if q["timestamp"] > cutoff]
    _analytics["flashcard_reviews"] = [f for f in _analytics["flashcard_reviews"] if f["timestamp"] > cutoff]
    removed = (before_q - len(_analytics["quiz_scores"])) + (before_f - len(_analytics["flashcard_reviews"]))
    if removed:
        logger.info("Cleaned up %s old analytics entries", removed)
