"""Database Service — Manages Supabase connection with an in-memory fallback."""

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

# ===== IN-MEMORY FALLBACK STORAGE =====
_memory_usage: dict[int, dict] = {}
_memory_documents: dict[int, OrderedDict] = {}
_memory_active_doc: dict[int, str] = {}
MAX_DOCS_PER_USER = 5

# Pending Action: bot đang chờ user phản hồi gì
# Key: user_id -> {action, data, expires_at}
_memory_pending_action: dict[int | str, dict] = {}

# ===== DOCUMENT TEXT TEMPORARY STORAGE (for Q&A) =====
# Lưu text gốc tạm thời cho Q&A sessions — TTL 24h, tự cleanup
# Key: "user_id:doc_id" -> {"text": str, "expires_at": float}
_memory_doc_text_temp: dict[str, dict] = {}

# ===== Q&A COUNTER =====
# Đếm số câu Q&A đã hỏi cho mỗi document
# Key: "user_id:doc_id" -> count
_memory_qa_count: dict[str, int] = {}
QA_LIMIT_PER_DOC = 5

# ===== STUDY SESSION STORAGE =====
# Key: "user_id" -> serialized session dict (QuizSession or FlashcardSession)
# TTL: 24h (in-memory cleanup)
_memory_study_sessions: dict[str, dict] = {}


# ===== DB METHODS =====

def check_rate_limit(user_id: int) -> bool:
    """Check if user has exceeded daily free limit."""
    today = time.strftime("%Y-%m-%d")
    
    if supabase:
        try:
            response = supabase.table("user_usage").select("count").eq("user_id", user_id).eq("date", today).execute()
            count = response.data[0]["count"] if response.data else 0
            return count < config.FREE_DAILY_LIMIT
        except Exception as e:
            logger.error(f"Supabase check_rate_limit error: {e}")
            # Fallback to memory on db failure
    
    if user_id not in _memory_usage or _memory_usage[user_id]["date"] != today:
        _memory_usage[user_id] = {"date": today, "count": 0}
        
    return _memory_usage[user_id]["count"] < config.FREE_DAILY_LIMIT


def increment_usage(user_id: int):
    """Increment the user's daily usage count."""
    today = time.strftime("%Y-%m-%d")

    if supabase:
        try:
            response = supabase.table("user_usage").select("count").eq("user_id", user_id).eq("date", today).execute()
            if response.data:
                new_count = response.data[0]["count"] + 1
                supabase.table("user_usage").update({"count": new_count}).eq("user_id", user_id).eq("date", today).execute()
            else:
                supabase.table("user_usage").insert({"user_id": user_id, "date": today, "count": 1}).execute()
            return
        except Exception as e:
            logger.error(f"Supabase increment_usage error: {e}")

    # Fallback memory
    if user_id not in _memory_usage or _memory_usage[user_id]["date"] != today:
        _memory_usage[user_id] = {"date": today, "count": 0, "study_count": 0}
    _memory_usage[user_id]["count"] += 1


# ===== PREMIUM GATING: STUDY MODE LIMIT =====
def get_study_mode_count_today(user_id: int | str) -> int:
    """Lấy số study sessions đã dùng hôm nay."""
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


def save_document(user_id: int, doc_id: str, name: str, text: str, summary: str, doc_type: str = "file"):
    """Save document to user's session."""
    timestamp = time.time()
    
    # Auto-activate
    set_active_doc(user_id, doc_id)
    
    if supabase:
        try:
            supabase.table("documents").insert({
                "id": doc_id,
                "user_id": user_id,
                "name": name,
                "text": "[Đã dọn dẹp nội dung gốc để bảo mật nha! 🔒]",  # DB limit safeguard & privacy
                "summary": summary,
                "doc_type": doc_type,
                "timestamp": timestamp
            }).execute()
            
            # Clean up old documents (keep last MAX_DOCS_PER_USER)
            # Fetch all user documents ordered by timestamp desc
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

    _memory_documents[user_id][doc_id] = {
        "name": name,
        "text": "[Đã dọn dẹp nội dung gốc để bảo mật nha! 🔒]",
        "summary": summary,
        "timestamp": timestamp,
        "type": doc_type,
        "id": doc_id
    }

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

    # Cleanup Q&A counter và temp text
    qa_key = f"{user_id}:{doc_id}"
    if qa_key in _memory_qa_count:
        del _memory_qa_count[qa_key]
        logger.info("Deleted Q&A counter for user %s, doc %s", user_id, doc_id)
    if qa_key in _memory_doc_text_temp:
        del _memory_doc_text_temp[qa_key]
        logger.info("Deleted Q&A temp text for user %s, doc %s", user_id, doc_id)

    return deleted



# ===== PENDING ACTION METHODS =====

def set_pending_action(user_id: int | str, action: str, data: dict):
    """Đặt trạng thái chờ phản hồi. Tự hết hạn sau 5 phút."""
    _memory_pending_action[user_id] = {
        "action": action,
        "data": data,
        "expires_at": time.time() + 300,  # 5 phút
    }
    logger.info("Pending action set for user %s: %s", user_id, action)


def get_pending_action(user_id: int | str) -> dict | None:
    """Lấy pending action nếu còn hiệu lực."""
    pending = _memory_pending_action.get(user_id)
    if not pending:
        return None
    if time.time() > pending["expires_at"]:
        del _memory_pending_action[user_id]
        return None
    return pending


def clear_pending_action(user_id: int | str):
    """Xóa pending action sau khi xử lý xong."""
    _memory_pending_action.pop(user_id, None)

def delete_user_data(user_id: int | str):
    """Delete all data for a user to comply with privacy requests."""
    # Supabase deletion
    if supabase:
        try:
            supabase.table("documents").delete().eq("user_id", user_id).execute()
            supabase.table("user_usage").delete().eq("user_id", user_id).execute()
            supabase.table("user_state").delete().eq("user_id", user_id).execute()
            logger.info("Deleted user %s data from Supabase", user_id)
        except Exception as e:
            logger.error("Supabase delete_user_data error: %s", e)

    # In-memory deletion
    _memory_usage.pop(int(user_id) if str(user_id).isdigit() else user_id, None)
    _memory_documents.pop(int(user_id) if str(user_id).isdigit() else user_id, None)
    _memory_active_doc.pop(int(user_id) if str(user_id).isdigit() else user_id, None)
    _memory_pending_action.pop(user_id, None)
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
    """Lưu text gốc tạm thời cho Q&A sessions. TTL mặc định 24h."""
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
    """Lấy text gốc cho Q&A session. Trả về None nếu đã hết hạn."""
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
    """Gia hạn TTL cho text tạm (khi user tiếp tục hỏi). Returns True nếu thành công."""
    key = f"{user_id}:{doc_id}"
    entry = _memory_doc_text_temp.get(key)
    if not entry:
        return False
    entry["expires_at"] = time.time() + (ttl_hours * 3600)
    return True


def _cleanup_expired_doc_texts():
    """Dọn dẹp tất cả text tạm và Q&A counter đã hết hạn. Gọi lazy mỗi lần save."""
    now = time.time()
    expired_keys = [k for k, v in _memory_doc_text_temp.items() if now > v["expires_at"]]
    for k in expired_keys:
        del _memory_doc_text_temp[k]
        # Also cleanup Q&A counter cho doc này
        if k in _memory_qa_count:
            del _memory_qa_count[k]
            logger.info("Cleaned up Q&A counter for expired doc: %s", k)
    if expired_keys:
        logger.info("Cleaned up %s expired Q&A texts + counters", len(expired_keys))


# ===== Q&A COUNTER =====
def get_qa_count(user_id: int | str, doc_id: str) -> int:
    """Lấy số câu Q&A đã hỏi cho document này."""
    # Normalize user_id to match storage format
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id
    key = f"{norm_user_id}:{doc_id}"
    return _memory_qa_count.get(key, 0)


def increment_qa_count(user_id: int | str, doc_id: str) -> int:
    """Tăng counter Q&A. Trả về số câu đã hỏi (sau khi tăng)."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id
    key = f"{norm_user_id}:{doc_id}"
    _memory_qa_count[key] = _memory_qa_count.get(key, 0) + 1
    return _memory_qa_count[key]


def reset_qa_count(user_id: int | str, doc_id: str):
    """Reset counter (khi user gửi file mới)."""
    norm_user_id = int(user_id) if str(user_id).isdigit() else user_id
    key = f"{norm_user_id}:{doc_id}"
    _memory_qa_count.pop(key, None)


# ===== STUDY SESSION STORAGE =====
# Key: "user_id" -> serialized session dict (QuizSession or FlashcardSession)
# TTL: 24h (in-memory cleanup)

def save_study_session(user_id: str, doc_id: str, session_type: str, session_data: dict) -> bool:
    """Lưu study session vào memory (và Supabase nếu có) với TTL 24h."""
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
                # Upsert vào bảng study_sessions
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
    """Load study session từ memory (và Supabase nếu có). Validate TTL 24h."""
    try:
        key = f"study:{user_id}"
        now = time.time()

        # Check memory first
        if key in _memory_study_sessions:
            rec = _memory_study_sessions[key]
            # Validate TTL
            if rec.get("expires_at", 0) < now:
                # Expired, delete và fallthrough to reload
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
    """Xóa study session (khi user thoát hoặc hết quiz)."""
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
    """Dọn study sessions cũ (TTL 24h) từ memory và Supabase."""
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



