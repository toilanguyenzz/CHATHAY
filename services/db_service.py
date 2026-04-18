"""Database Service — Manages Supabase connection with an in-memory fallback."""

import logging
import time
from collections import OrderedDict
from supabase import create_client, Client
from config import config

logger = logging.getLogger(__name__)

# Try to initialize Supabase client
supabase: Client | None = None
if config.SUPABASE_URL and config.SUPABASE_KEY:
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

# ===== VAULT & PENDING ACTION (SMART BOT) =====
# Vault: lưu mật khẩu/tài khoản mã hóa cho từng user
# Key: user_id -> list of {app_name, url, username, password, saved_at}
_memory_vault: dict[int | str, list[dict]] = {}

# Pending Action: bot đang chờ user phản hồi gì
# Key: user_id -> {action, data, expires_at}
# action: "confirm_save_vault" | "ask_name_for_task" | None
_memory_pending_action: dict[int | str, dict] = {}


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
        _memory_usage[user_id] = {"date": today, "count": 0}
    _memory_usage[user_id]["count"] += 1


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
                "text": text[:15000],  # DB limit safeguard
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
        "text": text[:15000],
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


# ===== VAULT METHODS =====

def save_vault_credential(user_id: int | str, app_name: str, url: str, username: str, password: str):
    """Lưu một credential vào vault của user."""
    if user_id not in _memory_vault:
        _memory_vault[user_id] = []

    # Kiểm tra trùng → cập nhật
    for cred in _memory_vault[user_id]:
        if cred["app_name"].lower() == app_name.lower():
            cred["url"] = url
            cred["username"] = username
            cred["password"] = password
            cred["saved_at"] = time.strftime("%Y-%m-%d %H:%M")
            logger.info("Vault updated credential '%s' for user %s", app_name, user_id)
            return

    _memory_vault[user_id].append({
        "app_name": app_name,
        "url": url,
        "username": username,
        "password": password,
        "saved_at": time.strftime("%Y-%m-%d %H:%M"),
    })
    logger.info("Vault saved credential '%s' for user %s", app_name, user_id)


def get_vault_credential(user_id: int | str, keyword: str) -> dict | None:
    """Tìm credential theo keyword (tên app/URL). Fuzzy match."""
    if user_id not in _memory_vault:
        return None

    keyword_lower = keyword.lower().strip()
    for cred in _memory_vault[user_id]:
        if (keyword_lower in cred["app_name"].lower()
                or keyword_lower in cred.get("url", "").lower()):
            return cred
    return None


def list_vault_credentials(user_id: int | str) -> list[dict]:
    """Liệt kê tất cả credentials của user (ẩn mật khẩu)."""
    if user_id not in _memory_vault:
        return []
    result = []
    for cred in _memory_vault[user_id]:
        result.append({
            "app_name": cred["app_name"],
            "url": cred.get("url", ""),
            "username": cred["username"],
            "saved_at": cred.get("saved_at", ""),
        })
    return result


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

