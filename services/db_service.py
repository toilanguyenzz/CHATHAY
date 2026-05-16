"""Database Service â€” Manages Supabase connection with an in-memory fallback."""

import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any
from config import config

logger = logging.getLogger(__name__)

try:
    from supabase import create_client
except Exception as exc:
    create_client = None
    logger.warning("Supabase SDK unavailable, using in-memory DB fallback: %s", exc)

# Try to initialize Supabase client
supabase: Any | None = None
if create_client and config.SUPABASE_URL and config.SUPABASE_KEY:
    try:
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client, falling back to in-memory: {e}")

def get_supabase_client():
    """Tráº£ vá» Supabase client hiá»‡n táº¡i."""
    return supabase

# ===== IN-MEMORY FALLBACK STORAGE =====
_memory_usage: dict[int, dict] = {}
_memory_documents: dict[int, OrderedDict] = {}
_memory_active_doc: dict[int, str] = {}
MAX_DOCS_PER_USER = 5

# Pending Action: bot Ä‘ang chá» user pháº£n há»“i gÃ¬
# Key: user_id -> {action, data, expires_at}
_memory_pending_action: dict[int | str, dict] = {}

# ===== DOCUMENT TEXT TEMPORARY STORAGE (for Q&A) =====
# LÆ°u text gá»‘c táº¡m thá»i cho Q&A sessions â€” TTL 24h, tá»± cleanup
# Key: "user_id:doc_id" -> {"text": str, "expires_at": float}
_memory_doc_text_temp: dict[str, dict] = {}

# ===== Q&A COUNTER =====
# Äáº¿m sá»‘ cÃ¢u Q&A Ä‘Ã£ há»i cho má»—i document
# Key: "user_id:doc_id" -> count
_memory_qa_count: dict[str, int] = {}
QA_LIMIT_PER_DOC = 5

# ===== STUDY SESSION STORAGE =====
# Key: "user_id" -> serialized session dict (QuizSession or FlashcardSession)
# TTL: 24h (in-memory cleanup)
_memory_study_sessions: dict[str, dict] = {}

# ===== SOLVED PROBLEMS STORAGE =====
# Key: "user_id" -> list of solved problem records (ordered by timestamp desc)
_memory_solved_problems: dict[str, list[dict]] = {}


# ===== DB METHODS =====

def check_rate_limit(user_id: int | str, limit_type: str = "general", period_hours: int = 24, max_requests: int | None = None) -> bool:
    """
    Check if user has exceeded rate limit for a specific action.

    Args:
        user_id: User identifier
        limit_type: Type of action ("general", "chat", "study", "upload")
        period_hours: Time window in hours
        max_requests: Override default limit for this type

    Returns:
        True if under limit, False if exceeded
    """
    today = time.strftime("%Y-%m-%d")
    norm_user_id = int(user_id) if str(user_id).isdigit() else str(user_id)

    # Determine limit based on type
    if max_requests is None:
        limits = {
            "general": config.FREE_DAILY_LIMIT,
            "chat": 5,
            "chat_doc": 5,
            "study": config.FREE_STUDY_SESSIONS_PER_DAY,
            "upload": 5,
        }
        limit = limits.get(limit_type, config.FREE_DAILY_LIMIT)
    else:
        limit = max_requests

    # Check Supabase
    if supabase:
        try:
            # Use composite key: user_id + action_type for per-action limits
            response = supabase.table("user_usage")\
                .select("count")\
                .eq("user_id", norm_user_id)\
                .eq("date", today)\
                .eq("action_type", limit_type)\
                .execute()
            count = response.data[0]["count"] if response.data else 0
            return count < limit
        except Exception as e:
            logger.error(f"Supabase check_rate_limit error: {e}")

    # Fallback memory
    memory_key = f"{norm_user_id}:{limit_type}"
    if memory_key not in _memory_usage or _memory_usage[memory_key]["date"] != today:
        _memory_usage[memory_key] = {"date": today, "count": 0}

    return _memory_usage[memory_key]["count"] < limit


def increment_usage(user_id: int | str, action_type: str = "general", amount: int = 1):
    """
    Increment the user's usage count for a specific action.

    Args:
        user_id: User identifier
        action_type: Type of action ("general", "chat", "study", "upload", "chat_doc")
        amount: Amount to increment (default 1)
    """
    today = time.strftime("%Y-%m-%d")
    norm_user_id = int(user_id) if str(user_id).isdigit() else str(user_id)

    if supabase:
        try:
            # Try to update existing record
            response = supabase.table("user_usage")\
                .select("count")\
                .eq("user_id", norm_user_id)\
                .eq("date", today)\
                .eq("action_type", action_type)\
                .execute()

            if response.data:
                new_count = response.data[0]["count"] + amount
                supabase.table("user_usage")\
                    .update({"count": new_count})\
                    .eq("user_id", norm_user_id)\
                    .eq("date", today)\
                    .eq("action_type", action_type)\
                    .execute()
            else:
                supabase.table("user_usage")\
                    .insert({"user_id": norm_user_id, "date": today, "count": amount, "action_type": action_type})\
                    .execute()
            return
        except Exception as e:
            logger.error(f"Supabase increment_usage error: {e}")

    # Fallback memory - use composite key
    memory_key = f"{norm_user_id}:{action_type}"
    if memory_key not in _memory_usage or _memory_usage[memory_key]["date"] != today:
        _memory_usage[memory_key] = {"date": today, "count": 0}
    _memory_usage[memory_key]["count"] += amount


# ===== PREMIUM GATING: STUDY MODE LIMIT =====
def get_study_mode_count_today(user_id: int | str) -> int:
    """Láº¥y sá»‘ study sessions Ä‘Ã£ dÃ¹ng hÃ´m nay."""
    today = time.strftime("%Y-%m-%d")
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id

    if supabase:
        try:
            response = supabase.table("user_usage").select("study_count").eq("user_id", norm_user_id).eq("date", today).execute()
            if response.data:
                return response.data[0].get("study_count", 0)
            return 0
        except Exception as e:
            logger.error(f"Supabase get_study_mode_count_today error: {e}")

    # Fallback memory
    if norm_user_id in _memory_usage and _memory_usage[norm_user_id]["date"] == today:
        return _memory_usage[norm_user_id].get("study_count", 0)
    return 0


def check_study_mode_limit(user_id: int | str) -> bool:
    """Check if user has exceeded free study sessions per day."""
    today = time.strftime("%Y-%m-%d")
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id

    if supabase:
        try:
            response = supabase.table("user_usage").select("study_count").eq("user_id", norm_user_id).eq("date", today).execute()
            count = response.data[0]["study_count"] if response.data else 0
            return count < config.FREE_STUDY_SESSIONS_PER_DAY
        except Exception as e:
            logger.error(f"Supabase check_study_mode_limit error: {e}")
            # Fallback to memory on db failure

    # Fallback memory
    if norm_user_id not in _memory_usage or _memory_usage[norm_user_id]["date"] != today:
        _memory_usage[norm_user_id] = {"date": today, "count": _memory_usage.get(norm_user_id, {}).get("count", 0), "study_count": 0}

    return _memory_usage[norm_user_id]["study_count"] < config.FREE_STUDY_SESSIONS_PER_DAY


def increment_study_mode_usage(user_id: int):
    """Increment the user's daily study session count."""
    today = time.strftime("%Y-%m-%d")

    if supabase:
        try:
            response = supabase.table("user_usage").select("study_count").eq("user_id", user_id).eq("date", today).execute()
            if response.data:
                new_count = response.data[0]["study_count"] + 1
                supabase.table("user_usage").update({"study_count": new_count}).eq("user_id", user_id).eq("date", today).execute()
            else:
                supabase.table("user_usage").insert({"user_id": user_id, "date": today, "study_count": 1}).execute()
            return
        except Exception as e:
            logger.error(f"Supabase increment_study_mode_usage error: {e}")

    # Fallback memory
    if user_id not in _memory_usage or _memory_usage[user_id]["date"] != today:
        _memory_usage[user_id] = {"date": today, "count": _memory_usage.get(user_id, {}).get("count", 0), "study_count": 0}
    _memory_usage[user_id]["study_count"] += 1


def save_document(user_id: int, doc_id: str, name: str, text: str, summary: str,
                  doc_type: str = "file", flashcards=None, quiz_questions=None, content=None):
    """Save document to user's session.

    Args:
        flashcards: List of flashcard objects [{front, back, difficulty}]
        quiz_questions: List of quiz question objects
        content: RAG content dict with chunks and embeddings
    """
    timestamp = time.time()

    # Auto-activate
    set_active_doc(user_id, doc_id)

    if supabase:
        try:
            data = {
                "id": doc_id,
                "user_id": user_id,
                "name": name,
                "text": "[ÄÃ£ dá»n dáº¹p ná»™i dung gá»‘c Ä‘á»ƒ báº£o máº­t nha! ðŸ”’]",  # DB limit safeguard & privacy
                "summary": summary,
                "doc_type": doc_type,
                "timestamp": timestamp
            }
            if flashcards is not None:
                data["flashcards"] = flashcards
            if quiz_questions is not None:
                data["quiz_questions"] = quiz_questions
            if content is not None:
                data["content"] = content

            supabase.table("documents").insert(data).execute()

            # Clean up old documents (keep last MAX_DOCS_PER_USER)
            docs = supabase.table("documents").select("id").eq("user_id", user_id).order("timestamp", desc=True).execute()
            if len(docs.data) > MAX_DOCS_PER_USER:
                ids_to_delete = [d["id"] for d in docs.data[MAX_DOCS_PER_USER:]]
                for del_id in ids_to_delete:
                    supabase.table("documents").delete().eq("id", del_id).execute()
            return
        except Exception as e:
            logger.error(f"Supabase save_document error: {e}")

    # Fallback memory
    if user_id not in _memory_documents:
        _memory_documents[user_id] = OrderedDict()

    doc_data = {
        "name": name,
        "text": "[ÄÃ£ dá»n dáº¹p ná»™i dung gá»‘c Ä‘á»ƒ báº£o máº­t nha! ðŸ”’]",
        "summary": summary,
        "timestamp": timestamp,
        "doc_type": doc_type,
    }
    if flashcards is not None:
        doc_data["flashcards"] = flashcards
    if quiz_questions is not None:
        doc_data["quiz_questions"] = quiz_questions
    if content is not None:
        doc_data["content"] = content

    _memory_documents[user_id][doc_id] = doc_data

    while len(_memory_documents[user_id]) > MAX_DOCS_PER_USER:
        _memory_documents[user_id].popitem(last=False)


def set_active_doc(user_id: int, doc_id: str):
    """Set the currently active document for a user."""
    if supabase:
        try:
            response = supabase.table("user_state").select("active_doc_id").eq("user_id", user_id).execute()
            if response.data:
                supabase.table("user_state").update({"active_doc_id": doc_id}).eq("user_id", user_id).execute()
            else:
                supabase.table("user_state").insert({"user_id": user_id, "active_doc_id": doc_id}).execute()
            return
        except Exception as e:
            logger.error(f"Supabase set_active_doc error: {e}")
            
    # Fallback memory
    _memory_active_doc[user_id] = doc_id


def get_active_doc(user_id: int) -> dict | None:
    """Get the active document info."""
    active_id = get_active_doc_id(user_id)
    if not active_id:
        return None
        
    if supabase:
        try:
            doc = supabase.table("documents").select("*").eq("id", active_id).execute()
            if doc.data:
                return doc.data[0]
            # ID found but document not in DB (deleted)
            return None
        except Exception as e:
            logger.error(f"Supabase get_active_doc error: {e}")
            
    # Fallback memory
    if user_id in _memory_documents and active_id in _memory_documents[user_id]:
        doc = _memory_documents[user_id][active_id]
        doc["id"] = active_id
        return doc
    return None
    

def get_active_doc_id(user_id: int) -> str | None:
    """Helper to just get the active document ID."""
    if supabase:
        try:
            state = supabase.table("user_state").select("active_doc_id").eq("user_id", user_id).execute()
            if state.data:
                return state.data[0]["active_doc_id"]
            return None
        except Exception as e:
            logger.error(f"Supabase get_active_doc_id error: {e}")
            
    # Fallback memory
    return _memory_active_doc.get(user_id)


def get_user_docs(user_id: int) -> list:
    """Get list of user documents (latest first)."""
    if supabase:
        try:
            docs = supabase.table("documents").select("*").eq("user_id", user_id).order("timestamp", desc=True).execute()
            return docs.data
        except Exception as e:
            logger.error(f"Supabase get_user_docs error: {e}")
            
    # Fallback memory
    if user_id not in _memory_documents:
        return []
        
    docs = []
    for doc_id, doc in reversed(_memory_documents[user_id].items()):
        doc_copy = doc.copy()
        doc_copy["id"] = doc_id
        docs.append(doc_copy)
    return docs


def delete_document_by_id(user_id: int, doc_id: str) -> bool:
    """Delete a single document by its ID. Returns True if deleted."""
    deleted = False

    if supabase:
        try:
            result = supabase.table("documents").delete().eq("id", doc_id).eq("user_id", user_id).execute()
            if result.data:
                deleted = True
                logger.info("Deleted document %s for user %s from Supabase", doc_id, user_id)
        except Exception as e:
            logger.error(f"Supabase delete_document_by_id error: {e}")

    # Memory fallback
    if user_id in _memory_documents and doc_id in _memory_documents[user_id]:
        del _memory_documents[user_id][doc_id]
        deleted = True
        logger.info("Deleted document %s for user %s from memory", doc_id, user_id)

    # If the deleted doc was active, clear active doc
    active_id = get_active_doc_id(user_id)
    if active_id == doc_id:
        if supabase:
            try:
                supabase.table("user_state").delete().eq("user_id", user_id).execute()
            except Exception:
                pass
        _memory_active_doc.pop(user_id, None)


def get_document_by_id(user_id: int | str, doc_id: str) -> dict | None:
    """Láº¥y document theo ID tá»« DB hoáº·c memory."""
    user_id_int = int(user_id) if str(user_id).isdigit() else user_id
    if supabase:
        try:
            response = supabase.table("documents")\
                .select("*")\
                .eq("id", doc_id)\
                .eq("user_id", user_id_int)\
                .execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.error(f"Supabase get_document_by_id error: {e}")

    # Fallback memory
    if user_id_int in _memory_documents and doc_id in _memory_documents[user_id_int]:
        doc = _memory_documents[user_id_int][doc_id].copy()
        doc["id"] = doc_id
        return doc
    return None


def save_document_content(doc_id: str, content: dict):
    """LÆ°u RAG content (chunks, embeddings) vÃ o document."""
    if supabase:
        try:
            supabase.table("documents")\
                .update({"content": content})\
                .eq("id", doc_id)\
                .execute()
        except Exception as e:
            logger.error(f"Supabase save_document_content error: {e}")
            # Still save to memory as fallback

    # Update memory (find in any user's documents)
    for user_docs in _memory_documents.values():
        if doc_id in user_docs:
            user_docs[doc_id]["content"] = content
            break

    # Note: Q&A cleanup is handled per-user in other methods



# ===== PENDING ACTION METHODS =====

def set_pending_action(user_id: int | str, action: str, data: dict):
    """Äáº·t tráº¡ng thÃ¡i chá» pháº£n há»“i. Tá»± háº¿t háº¡n sau 5 phÃºt."""
    _memory_pending_action[user_id] = {
        "action": action,
        "data": data,
        "expires_at": time.time() + 300,  # 5 phÃºt
    }
    logger.info("Pending action set for user %s: %s", user_id, action)


def get_pending_action(user_id: int | str) -> dict | None:
    """Láº¥y pending action náº¿u cÃ²n hiá»‡u lá»±c."""
    pending = _memory_pending_action.get(user_id)
    if not pending:
        return None
    if time.time() > pending["expires_at"]:
        del _memory_pending_action[user_id]
        return None
    return pending


def clear_pending_action(user_id: int | str):
    """XÃ³a pending action sau khi xá»­ lÃ½ xong."""
    _memory_pending_action.pop(user_id, None)

def delete_user_data(user_id: int | str):
    """Delete all data for a user to comply with privacy requests."""
    # Supabase deletion
    if supabase:
        try:
            supabase.table("documents").delete().eq("user_id", user_id).execute()
            supabase.table("user_usage").delete().eq("user_id", user_id).execute()
            supabase.table("user_state").delete().eq("user_id", user_id).execute()
            supabase.table("solved_problems").delete().eq("user_id", user_id).execute()
            logger.info("Deleted user %s data from Supabase", user_id)
        except Exception as e:
            logger.error("Supabase delete_user_data error: %s", e)

    # In-memory deletion
    _memory_usage.pop(int(user_id) if str(user_id).isdigit() else user_id, None)
    _memory_documents.pop(int(user_id) if str(user_id).isdigit() else user_id, None)
    _memory_active_doc.pop(int(user_id) if str(user_id).isdigit() else user_id, None)
    _memory_pending_action.pop(user_id, None)
    # Cleanup solved problems
    _memory_solved_problems.pop(int(user_id) if str(user_id).isdigit() else user_id, None)
    # Cleanup Q&A temp texts
    keys_to_delete = [k for k in _memory_doc_text_temp if k.startswith(f"{user_id}:")]
    for k in keys_to_delete:
        del _memory_doc_text_temp[k]
    # Cleanup Q&A counters
    qa_keys_to_delete = [k for k in _memory_qa_count if k.startswith(f"{user_id}:")]
    for k in qa_keys_to_delete:
        del _memory_qa_count[k]
    logger.info("Deleted user %s data from memory", user_id)


# ===== DOCUMENT TEXT TEMPORARY STORAGE (for Q&A) =====

def save_document_text_temp(user_id: int | str, doc_id: str, text: str, ttl_hours: int = 24):
    """LÆ°u text gá»‘c táº¡m thá»i cho Q&A sessions. TTL máº·c Ä‘á»‹nh 24h."""
    key = f"{user_id}:{doc_id}"
    _memory_doc_text_temp[key] = {
        "text": text,
        "expires_at": time.time() + (ttl_hours * 3600),
    }
    logger.info("Saved temp text for Q&A: user=%s, doc=%s, len=%s chars, TTL=%sh",
                user_id, doc_id, len(text), ttl_hours)
    # Auto-cleanup expired entries (lazy cleanup)
    _cleanup_expired_doc_texts()


def get_document_text_temp(user_id: int | str, doc_id: str) -> str | None:
    """Láº¥y text gá»‘c cho Q&A session. Tráº£ vá» None náº¿u Ä‘Ã£ háº¿t háº¡n."""
    key = f"{user_id}:{doc_id}"
    entry = _memory_doc_text_temp.get(key)
    if not entry:
        return None
    if time.time() > entry["expires_at"]:
        del _memory_doc_text_temp[key]
        logger.info("Q&A text expired for user=%s, doc=%s", user_id, doc_id)
        return None
    return entry["text"]


def renew_document_text_temp(user_id: int | str, doc_id: str, ttl_hours: int = 24) -> bool:
    """Gia háº¡n TTL cho text táº¡m (khi user tiáº¿p tá»¥c há»i). Returns True náº¿u thÃ nh cÃ´ng."""
    key = f"{user_id}:{doc_id}"
    entry = _memory_doc_text_temp.get(key)
    if not entry:
        return False
    entry["expires_at"] = time.time() + (ttl_hours * 3600)
    return True


def _cleanup_expired_doc_texts():
    """Dá»n dáº¹p táº¥t cáº£ text táº¡m vÃ  Q&A counter Ä‘Ã£ háº¿t háº¡n. Gá»i lazy má»—i láº§n save."""
    now = time.time()
    expired_keys = [k for k, v in _memory_doc_text_temp.items() if now > v["expires_at"]]
    for k in expired_keys:
        del _memory_doc_text_temp[k]
        # Also cleanup Q&A counter cho doc nÃ y
        if k in _memory_qa_count:
            del _memory_qa_count[k]
            logger.info("Cleaned up Q&A counter for expired doc: %s", k)
    if expired_keys:
        logger.info("Cleaned up %s expired Q&A texts + counters", len(expired_keys))


# ===== Q&A COUNTER =====
def get_qa_count(user_id: int | str, doc_id: str) -> int:
    """Láº¥y sá»‘ cÃ¢u Q&A Ä‘Ã£ há»i cho document nÃ y."""
    # Normalize user_id to match storage format
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id
    key = f"{norm_user_id}:{doc_id}"
    return _memory_qa_count.get(key, 0)


def increment_qa_count(user_id: int | str, doc_id: str) -> int:
    """TÄƒng counter Q&A. Tráº£ vá» sá»‘ cÃ¢u Ä‘Ã£ há»i (sau khi tÄƒng)."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id
    key = f"{norm_user_id}:{doc_id}"
    _memory_qa_count[key] = _memory_qa_count.get(key, 0) + 1
    return _memory_qa_count[key]


def reset_qa_count(user_id: int | str, doc_id: str):
    """Reset counter (khi user gá»­i file má»›i)."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id
    key = f"{norm_user_id}:{doc_id}"
    _memory_qa_count.pop(key, None)


# ===== STUDY SESSION STORAGE =====
# Key: "user_id" -> serialized session dict (QuizSession or FlashcardSession)
# TTL: 24h (in-memory cleanup)

def save_study_session(user_id: str, doc_id: str, session_type: str, session_data: dict) -> bool:
    """LÆ°u study session vÃ o memory (vÃ  Supabase náº¿u cÃ³) vá»›i TTL 24h."""
    try:
        key = f"study:{user_id}"
        now = time.time()
        session_record = {
            "doc_id": doc_id,
            "session_type": session_type,
            "data": session_data,
            "created_at": now,
            "expires_at": now + 24 * 3600,  # 24h TTL
            "updated_at": now,
        }
        _memory_study_sessions[key] = session_record

        if supabase:
            try:
                # Upsert vÃ o báº£ng study_sessions
                supabase.table("study_sessions").upsert({
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "mode": session_type,
                    "state": session_data,
                    "created_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                    "expires_at": datetime.fromtimestamp(now + 24*3600, tz=timezone.utc).isoformat(),
                    "updated_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                }).execute()
            except Exception as e:
                logger.warning(f"Supabase save_study_session error: {e}")

        return True
    except Exception as e:
        logger.error(f"save_study_session failed: {e}")
        return False


def load_study_session(user_id: str) -> dict | None:
    """Load study session tá»« memory (vÃ  Supabase náº¿u cÃ³). Validate TTL 24h."""
    try:
        key = f"study:{user_id}"
        now = time.time()

        # Check memory first
        if key in _memory_study_sessions:
            rec = _memory_study_sessions[key]
            # Validate TTL
            if rec.get("expires_at", 0) < now:
                # Expired, delete vÃ  fallthrough to reload
                _memory_study_sessions.pop(key, None)
                if supabase:
                    try:
                        supabase.table("study_sessions").delete().eq("user_id", user_id).execute()
                    except Exception:
                        pass
            else:
                return rec

        # Load from Supabase if not in memory or expired
        if supabase:
            try:
                result = supabase.table("study_sessions").select("*").eq("user_id", user_id).execute()
                if result.data:
                    record = result.data[0]

                    # Convert ISO datetime to float timestamp
                    def iso_to_ts(iso_str: str) -> float:
                        try:
                            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
                            return dt.timestamp()
                        except Exception:
                            return now

                    updated_ts = iso_to_ts(record["updated_at"])
                    created_ts = iso_to_ts(record.get("created_at", record["updated_at"]))

                    # Determine expires_at: if present use it, else compute from updated_at
                    if record.get("expires_at"):
                        expires_ts = iso_to_ts(record["expires_at"])
                    else:
                        expires_ts = updated_ts + 24 * 3600

                    session_rec = {
                        "doc_id": record.get("doc_id", "unknown"),
                        "session_type": record["mode"],
                        "data": record["session_data"],
                        "created_at": created_ts,
                        "expires_at": expires_ts,
                        "updated_at": updated_ts,
                    }

                    # Validate TTL
                    if session_rec["expires_at"] < now:
                        # Expired, delete from DB
                        try:
                            supabase.table("study_sessions").delete().eq("user_id", user_id).execute()
                        except Exception:
                            pass
                        return None

                    # Cache to memory
                    _memory_study_sessions[key] = session_rec
                    return session_rec
            except Exception as e:
                logger.warning(f"Supabase load_study_session error: {e}")

        return None
    except Exception as e:
        logger.error(f"load_study_session failed: {e}")
        return None


def clear_study_session(user_id: str) -> bool:
    """XÃ³a study session (khi user thoÃ¡t hoáº·c háº¿t quiz)."""
    try:
        key = f"study:{user_id}"
        _memory_study_sessions.pop(key, None)

        if supabase:
            try:
                supabase.table("study_sessions").delete().eq("user_id", user_id).execute()
            except Exception as e:
                logger.warning(f"Supabase clear_study_session error: {e}")

        return True
    except Exception as e:
        logger.error(f"clear_study_session failed: {e}")
        return False


def _cleanup_expired_study_sessions():
    """Dá»n study sessions cÅ© (TTL 24h) tá»« memory vÃ  Supabase."""
    now = time.time()
    expired_keys = []
    for key, sess in _memory_study_sessions.items():
        if now - sess.get("updated_at", 0) > 24 * 3600:
            expired_keys.append(key)
    for key in expired_keys:
        del _memory_study_sessions[key]
    if expired_keys:
        logger.info(f"Cleaned up {len(expired_keys)} expired study sessions from memory")

    # Supabase cleanup via RPC
    if supabase:
        try:
            result = supabase.rpc("cleanup_expired_study_sessions").execute()
            if result.data:
                deleted = result.data[0] if isinstance(result.data[0], int) else 0
                if deleted:
                    logger.info(f"Cleaned up {deleted} expired study sessions from Supabase")
        except Exception as e:
            logger.warning(f"Supabase cleanup_expired_study_sessions error: {e}")


# ===== SOLVED PROBLEMS METHODS =====

def save_solved_problem(
    user_id: int | str,
    question: str,
    steps: list[str],
    answer: str,
    subject: str | None = None,
    difficulty: str | None = None,
    image_url: str | None = None
):
    """LÆ°u bÃ i táº­p Ä‘Ã£ giáº£i vÃ o database."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id
    problem_id = f"prob_{int(time.time())}_{hash(question) % 10000}"
    timestamp = time.time()
    from datetime import datetime, timezone
    created_at_iso = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    problem_data = {
        "id": problem_id,
        "user_id": norm_user_id,
        "question": question[:500],  # limit length
        "steps": steps,
        "answer": answer[:200],
        "subject": subject,
        "difficulty": difficulty,
        "image_url": image_url,
        "created_at": created_at_iso,
    }

    if supabase:
        try:
            supabase.table("solved_problems").insert(problem_data).execute()
            logger.info("Saved solved problem %s for user %s to Supabase", problem_id, norm_user_id)
            return problem_id
        except Exception as e:
            logger.error(f"Supabase save_solved_problem error: {e}")

    # Fallback memory
    if norm_user_id not in _memory_solved_problems:
        _memory_solved_problems[norm_user_id] = []
    _memory_solved_problems[norm_user_id].insert(0, problem_data)
    # Keep only last 50 problems per user in memory
    _memory_solved_problems[norm_user_id] = _memory_solved_problems[norm_user_id][:50]
    logger.info("Saved solved problem %s for user %s to memory", problem_id, norm_user_id)
    return problem_id


def get_solved_problems(user_id: int | str, limit: int = 10) -> list[dict]:
    """Láº¥y danh sÃ¡ch bÃ i táº­p Ä‘Ã£ giáº£i cá»§a user."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id

    if supabase:
        try:
            result = supabase.table("solved_problems")\
                .select("*")\
                .eq("user_id", norm_user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Supabase get_solved_problems error: {e}")

    # Fallback memory
    return _memory_solved_problems.get(norm_user_id, [])[:limit]


def delete_solved_problem(user_id: int | str, problem_id: str) -> bool:
    """XÃ³a má»™t bÃ i táº­p Ä‘Ã£ giáº£i."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id
    deleted = False

    if supabase:
        try:
            supabase.table("solved_problems")\
                .delete()\
                .eq("id", problem_id)\
                .eq("user_id", norm_user_id)\
                .execute()
            deleted = True
            logger.info("Deleted solved problem %s for user %s from Supabase", problem_id, norm_user_id)
        except Exception as e:
            logger.error(f"Supabase delete_solved_problem error: {e}")

    # Memory fallback
    if norm_user_id in _memory_solved_problems:
        before = len(_memory_solved_problems[norm_user_id])
        _memory_solved_problems[norm_user_id] = [
            p for p in _memory_solved_problems[norm_user_id]
            if p["id"] != problem_id
        ]
        if len(_memory_solved_problems[norm_user_id]) < before:
            deleted = True
            logger.info("Deleted solved problem %s for user %s from memory", problem_id, norm_user_id)

    return deleted







# ===== COIN SYSTEM METHODS =====

def get_coin_balance(user_id: int | str) -> int:
    """Láº¥y sá»‘ dÆ° Coin cá»§a user."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id

    if supabase:
        try:
            result = supabase.table("user_usage").select("coin_balance").eq("user_id", norm_user_id).single().execute()
            return result.data.get("coin_balance", 0) if result.data else 0
        except Exception as e:
            logger.error(f"Supabase get_coin_balance error: {e}")

    # Fallback memory
    return _memory_usage.get(norm_user_id, {}).get("coin_balance", 0)


def update_coin_balance(user_id: int | str, new_balance: int) -> bool:
    """Cáº­p nháº­t sá»‘ dÆ° Coin."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id

    if supabase:
        try:
            supabase.table("user_usage").update({"coin_balance": new_balance}).eq("user_id", norm_user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase update_coin_balance error: {e}")

    # Fallback memory
    if norm_user_id not in _memory_usage:
        _memory_usage[norm_user_id] = {"date": time.strftime("%Y-%m-%d"), "count": 0, "study_count": 0}
    _memory_usage[norm_user_id]["coin_balance"] = new_balance
    return True


def log_coin_transaction(user_id: int | str, amount: int, trans_type: str, reason: str, balance_after: int):
    """Ghi log giao dá»‹ch Coin."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id

    if supabase:
        try:
            supabase.table("coin_transactions").insert({
                "user_id": norm_user_id,
                "amount": amount,
                "type": trans_type,
                "reason": reason,
                "balance_after": balance_after,
            }).execute()
        except Exception as e:
            logger.error(f"Supabase log_coin_transaction error: {e}")


def get_coin_transactions(user_id: int | str, limit: int = 20):
    """Láº¥y lá»‹ch sá»­ giao dá»‹ch Coin."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id

    if supabase:
        try:
            result = supabase.table("coin_transactions").select("*").eq("user_id", norm_user_id).order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Supabase get_coin_transactions error: {e}")

    return []


def get_user_by_zalo_id(zalo_user_id: str) -> dict | None:
    """Láº¥y user theo Zalo ID."""
    if supabase:
        try:
            result = supabase.table("user_usage").select("*").eq("user_id", zalo_user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase get_user_by_zalo_id error: {e}")
    return None


# ===== DATABASE MIGRATION HELPER =====

def ensure_solved_problems_table():
    """Ensure solved_problems table exists. Auto-create on startup if missing."""
    if not supabase:
        logger.warning("Supabase not available, skipping table check")
        return

    try:
        # Quick check if table exists
        supabase.table("solved_problems").select("count").limit(1).execute()
        logger.debug("Table solved_problems exists")
        return
    except Exception as e:
        if "PGRST205" in str(e) or "not found" in str(e).lower():
            logger.info("Table solved_problems not found, attempting to create...")
            _create_solved_problems_table()
        else:
            logger.error(f"Error checking solved_problems table: {e}")


def _create_solved_problems_table():
    """Create solved_problems table using raw SQL via psycopg2."""
    try:
        import psycopg2
        from pathlib import Path
        import os

        # Get connection string from env
        db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_CONNECTION_STRING")
        if not db_url:
            logger.error("Cannot create table: DATABASE_URL or SUPABASE_CONNECTION_STRING not set")
            logger.info("Please run migrations manually - see MIGRATION_GUIDE.md")
            return

        # Read migration SQL
        sql_path = Path(__file__).parent.parent / "migrations" / "005_add_solved_problems.sql"
        if not sql_path.exists():
            logger.error(f"Migration file not found: {sql_path}")
            return

        sql = sql_path.read_text(encoding="utf-8")

        # Connect and execute
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()

        # Split statements
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        for stmt in statements:
            try:
                cur.execute(stmt)
            except Exception as stmt_err:
                # Ignore "already exists" errors
                if "already exists" in str(stmt_err).lower():
                    logger.debug(f"Object already exists: {stmt[:50]}...")
                else:
                    logger.warning(f"Statement failed: {stmt_err}")

        cur.close()
        conn.close()
        logger.info("✅ Table solved_problems created successfully")

    except ImportError:
        logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
        logger.info("Please run migrations manually - see MIGRATION_GUIDE.md")
    except Exception as e:
        logger.error(f"Failed to create solved_problems table: {e}")
        logger.info("Please run migrations manually - see MIGRATION_GUIDE.md")


# Call on module import (server startup)
if supabase:
    ensure_solved_problems_table()
