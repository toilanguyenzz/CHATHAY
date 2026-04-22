"""Token Store — SQLite-based persistent storage for Zalo OAuth tokens.

v3.0 — Fix triệt để lỗi "Invalid refresh token" sau redeploy:
  - Retry đọc DB nếu Volume chưa mount kịp
  - LUÔN ưu tiên DB (token mới nhất) > env vars (token cũ từ Dashboard)
  - Log rõ nguồn gốc token để debug
  - So sánh updated_at để biết token nào mới hơn
"""

import logging
import os
import sqlite3
import time
from typing import Any

logger = logging.getLogger(__name__)

# Thư mục data — trên Railway nên mount Volume vào /data
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
    logger.info("Token store initialized at: %s", DB_PATH)


def _init_db_with_retry(max_retries: int = 3, delay: float = 2.0):
    """Khởi tạo DB với retry — phòng trường hợp Railway Volume chưa mount kịp."""
    for attempt in range(max_retries):
        try:
            _ensure_db()
            return True
        except Exception as e:
            logger.warning("DB init attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                time.sleep(delay)
    logger.error("Could not initialize token store DB after %d attempts!", max_retries)
    return False


# Khởi tạo DB ngay khi import (với retry)
_db_ready = _init_db_with_retry()


def save_token(key: str, value: str) -> bool:
    """Lưu một token vào DB."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("""
            INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """, (key, value, time.time()))
        conn.commit()
        conn.close()
        logger.info("Token saved: %s (len=%s)", key, len(value))
        return True
    except Exception as e:
        logger.error("Failed to save token %s: %s", key, e)
        return False


def load_token(key: str, fallback: str = "") -> str:
    """Đọc token từ DB. Nếu DB có giá trị → dùng DB. Nếu không → dùng fallback (env var)."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.execute("SELECT value, updated_at FROM kv_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            db_value = row[0]
            updated = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[1]))
            logger.info("Token loaded from DB: %s (len=%s, updated=%s)", key, len(db_value), updated)
            return db_value
        else:
            logger.info("Token NOT found in DB for key=%s, using fallback (len=%s)", key, len(fallback))
    except Exception as e:
        logger.warning("Failed to load token %s from DB: %s — using fallback", key, e)

    return fallback


def save_tokens(access_token: str, refresh_token: str) -> bool:
    """Lưu cả cặp access_token + refresh_token."""
    ok1 = save_token("zalo_access_token", access_token)
    ok2 = save_token("zalo_refresh_token", refresh_token)
    return ok1 and ok2


def load_tokens(env_access: str = "", env_refresh: str = "") -> tuple[str, str]:
    """Load cả cặp token. 
    
    Logic ưu tiên: DB > env vars.
    Chỉ dùng env vars nếu DB TRỐNG (lần deploy đầu tiên).
    Nếu DB có token → LUÔN dùng DB, bất kể env vars là gì.
    """
    access = load_token("zalo_access_token", env_access)
    refresh = load_token("zalo_refresh_token", env_refresh)

    # Log rõ nguồn gốc để debug
    access_source = "DB" if access != env_access else ("ENV" if access else "EMPTY")
    refresh_source = "DB" if refresh != env_refresh else ("ENV" if refresh else "EMPTY")
    logger.info("Token sources — Access: %s (ends: ...%s), Refresh: %s (ends: ...%s)",
                access_source, access[-8:] if len(access) > 8 else "***",
                refresh_source, refresh[-8:] if len(refresh) > 8 else "***")

    return access, refresh


def get_token_info() -> dict[str, Any]:
    """Xem trạng thái token hiện tại (cho debug endpoint)."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.execute("SELECT key, length(value), updated_at FROM kv_store")
        rows = cursor.fetchall()
        conn.close()
        return {
            "db_path": DB_PATH,
            "db_ready": _db_ready,
            "tokens": [
                {
                    "key": row[0],
                    "value_length": row[1],
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[2]))
                }
                for row in rows
            ]
        }
    except Exception as e:
        return {"error": str(e), "db_ready": _db_ready}
