"""Token Store — SQLite-based persistent storage for Zalo OAuth tokens.

Giải quyết vấn đề: Khi Railway restart (deploy mới, crash, scale),
token mới nhất bị mất vì chỉ lưu trong memory/biến môi trường.
SQLite file lưu trên Railway Volume → sống sót qua mọi lần restart.
"""

import json
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


# Khởi tạo DB ngay khi import
try:
    _ensure_db()
except Exception as e:
    logger.warning("Could not initialize token store DB: %s", e)


def save_token(key: str, value: str) -> bool:
    """Lưu một token vào DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            logger.info("Token loaded from DB: %s (len=%s)", key, len(row[0]))
            return row[0]
    except Exception as e:
        logger.warning("Failed to load token %s from DB: %s", key, e)
    
    return fallback


def save_tokens(access_token: str, refresh_token: str) -> bool:
    """Lưu cả cặp access_token + refresh_token."""
    ok1 = save_token("zalo_access_token", access_token)
    ok2 = save_token("zalo_refresh_token", refresh_token)
    return ok1 and ok2


def load_tokens(env_access: str = "", env_refresh: str = "") -> tuple[str, str]:
    """Load cả cặp token. Ưu tiên DB > env var."""
    access = load_token("zalo_access_token", env_access)
    refresh = load_token("zalo_refresh_token", env_refresh)
    return access, refresh


def get_token_info() -> dict[str, Any]:
    """Xem trạng thái token hiện tại (cho debug endpoint)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT key, length(value), updated_at FROM kv_store")
        rows = cursor.fetchall()
        conn.close()
        return {
            "db_path": DB_PATH,
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
        return {"error": str(e)}
