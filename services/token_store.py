"""Token Store v4.0 — Supabase (cloud) + SQLite (fallback).

FIX VĨNH VIỄN lỗi "Invalid refresh token" sau redeploy:
  - Ưu tiên 1: SUPABASE (cloud DB, luôn online, không phụ thuộc Railway Volume)
  - Ưu tiên 2: SQLite trên Railway Volume (fallback nếu Supabase down)
  - Ưu tiên 3: Environment variables (token cũ từ Dashboard)
  
  Token được lưu trên cloud → deploy/restart bao nhiêu lần cũng không mất.
"""

import logging
import os
import sqlite3
import time
from typing import Any

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# SUPABASE CLIENT (PRIMARY)
# ═══════════════════════════════════════════════════════════════

_supabase = None

try:
    from config import config
    if config.SUPABASE_URL and config.SUPABASE_KEY:
        from supabase import create_client
        _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        logger.info("✅ Token store: Supabase connected (cloud mode)")
    else:
        logger.warning("⚠️ Token store: No Supabase credentials, using SQLite only")
except Exception as e:
    logger.warning("⚠️ Token store: Supabase init failed (%s), using SQLite fallback", e)


# ═══════════════════════════════════════════════════════════════
# SUPABASE METHODS
# ═══════════════════════════════════════════════════════════════

def _supabase_save(key: str, value: str) -> bool:
    """Lưu token vào Supabase cloud."""
    if not _supabase:
        return False
    try:
        _supabase.table("zalo_tokens").upsert({
            "key": key,
            "value": value,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }).execute()
        logger.info("☁️ Token saved to Supabase: %s (len=%s)", key, len(value))
        return True
    except Exception as e:
        logger.error("Supabase save failed for %s: %s", key, e)
        return False


def _supabase_load(key: str) -> str | None:
    """Đọc token từ Supabase cloud."""
    if not _supabase:
        return None
    try:
        response = _supabase.table("zalo_tokens").select("value, updated_at").eq("key", key).execute()
        if response.data and response.data[0].get("value"):
            value = response.data[0]["value"]
            updated = response.data[0].get("updated_at", "?")
            logger.info("☁️ Token loaded from Supabase: %s (len=%s, updated=%s)", key, len(value), updated)
            return value
        return None
    except Exception as e:
        logger.warning("Supabase load failed for %s: %s", key, e)
        return None


def _supabase_get_all() -> list[dict]:
    """Lấy tất cả tokens từ Supabase (cho debug)."""
    if not _supabase:
        return []
    try:
        response = _supabase.table("zalo_tokens").select("key, updated_at").execute()
        return [
            {
                "key": row["key"],
                "value_length": "stored",
                "updated_at": row.get("updated_at", "?"),
                "source": "supabase",
            }
            for row in response.data
        ]
    except Exception as e:
        logger.warning("Supabase get_all failed: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════
# SQLITE FALLBACK (SECONDARY)
# ═══════════════════════════════════════════════════════════════

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
DB_PATH = os.path.join(DATA_DIR, "tokens.db")


def _ensure_db():
    """Tạo database và bảng nếu chưa có."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kv_store (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _init_db_with_retry(max_retries: int = 3, delay: float = 2.0):
    """Khởi tạo DB với retry — phòng trường hợp Railway Volume chưa mount kịp."""
    for attempt in range(max_retries):
        try:
            _ensure_db()
            logger.info("SQLite token store ready at: %s", DB_PATH)
            return True
        except Exception as e:
            logger.warning("DB init attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                time.sleep(delay)
    logger.error("Could not initialize SQLite token store after %d attempts!", max_retries)
    return False


_db_ready = _init_db_with_retry()


def _sqlite_save(key: str, value: str) -> bool:
    """Lưu token vào SQLite local."""
    if not _db_ready:
        return False
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("""
            INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """, (key, value, time.time()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error("SQLite save failed for %s: %s", key, e)
        return False


def _sqlite_load(key: str) -> str | None:
    """Đọc token từ SQLite local."""
    if not _db_ready:
        return None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.execute("SELECT value, updated_at FROM kv_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
        return None
    except Exception as e:
        logger.warning("SQLite load failed for %s: %s", key, e)
        return None


# ═══════════════════════════════════════════════════════════════
# PUBLIC API — Dual-write, prioritized read
# ═══════════════════════════════════════════════════════════════

def save_token(key: str, value: str) -> bool:
    """Lưu token vào CẢ HAI nơi: Supabase (cloud) + SQLite (local).
    
    Dual-write đảm bảo token luôn có ít nhất 1 bản sao an toàn.
    """
    ok_cloud = _supabase_save(key, value)
    ok_local = _sqlite_save(key, value)
    
    if ok_cloud:
        logger.info("Token saved: %s → ☁️ Supabase ✅ + 💾 SQLite %s",
                     key, "✅" if ok_local else "❌")
    elif ok_local:
        logger.warning("Token saved: %s → ☁️ Supabase ❌ + 💾 SQLite ✅ (cloud failed!)", key)
    else:
        logger.error("❌ Token save COMPLETELY FAILED for %s!", key)
    
    return ok_cloud or ok_local


def load_token(key: str, fallback: str = "") -> str:
    """Đọc token theo thứ tự ưu tiên: Supabase → SQLite → env var.
    
    Supabase luôn có token mới nhất vì nó là cloud DB, không bị ảnh hưởng
    bởi Railway restart/deploy.
    """
    # 1. Supabase (cloud, luôn đáng tin nhất)
    value = _supabase_load(key)
    if value:
        return value
    
    # 2. SQLite (local, có thể bị stale sau deploy)
    value = _sqlite_load(key)
    if value:
        logger.info("Token loaded from SQLite fallback: %s (len=%s)", key, len(value))
        # Sync ngược lên Supabase nếu cloud đang trống
        _supabase_save(key, value)
        return value
    
    # 3. Environment variable (token cũ nhất, chỉ dùng lần đầu)
    if fallback:
        logger.info("Token loaded from env fallback: %s (len=%s)", key, len(fallback))
    return fallback


def save_tokens(access_token: str, refresh_token: str) -> bool:
    """Lưu cả cặp access_token + refresh_token."""
    ok1 = save_token("zalo_access_token", access_token)
    ok2 = save_token("zalo_refresh_token", refresh_token)
    return ok1 and ok2


def load_tokens(env_access: str = "", env_refresh: str = "") -> tuple[str, str]:
    """Load cả cặp token.
    
    Thứ tự ưu tiên: Supabase (cloud) > SQLite (local) > env vars.
    """
    access = load_token("zalo_access_token", env_access)
    refresh = load_token("zalo_refresh_token", env_refresh)

    logger.info("Tokens loaded — Access: %s chars (ends: ...%s), Refresh: %s chars (ends: ...%s)",
                len(access), access[-8:] if len(access) > 8 else "***",
                len(refresh), refresh[-8:] if len(refresh) > 8 else "***")

    return access, refresh


def get_token_info() -> dict[str, Any]:
    """Xem trạng thái token hiện tại (cho debug endpoint)."""
    info: dict[str, Any] = {
        "supabase_connected": _supabase is not None,
        "sqlite_ready": _db_ready,
        "sqlite_path": DB_PATH,
        "tokens": [],
    }
    
    # Supabase tokens
    cloud_tokens = _supabase_get_all()
    info["tokens"].extend(cloud_tokens)
    
    # SQLite tokens (nếu không có Supabase)
    if not cloud_tokens and _db_ready:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.execute("SELECT key, length(value), updated_at FROM kv_store")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                info["tokens"].append({
                    "key": row[0],
                    "value_length": row[1],
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[2])),
                    "source": "sqlite",
                })
        except Exception as e:
            info["sqlite_error"] = str(e)
    
    return info
