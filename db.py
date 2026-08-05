import sqlite3
import threading
from typing import Any, Dict, List, Optional

import config

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init() -> None:
    with _lock:
        c = conn()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS admins (
                user_id   INTEGER PRIMARY KEY,
                username  TEXT,
                added_by  INTEGER,
                added_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS channels (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id  INTEGER NOT NULL,
                chat_id   TEXT NOT NULL,
                title     TEXT,
                logo_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(owner_id, chat_id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                owner_id INTEGER NOT NULL,
                key      TEXT NOT NULL,
                value    TEXT,
                PRIMARY KEY (owner_id, key)
            );

            CREATE TABLE IF NOT EXISTS states (
                user_id INTEGER PRIMARY KEY,
                state   TEXT,
                payload TEXT
            );
            """
        )
        c.commit()


def add_admin(user_id: int, username: str = "", added_by: int = 0) -> None:
    with _lock:
        conn().execute(
            "INSERT OR REPLACE INTO admins (user_id, username, added_by) VALUES (?,?,?)",
            (user_id, username, added_by),
        )
        conn().commit()


def remove_admin(user_id: int) -> None:
    with _lock:
        conn().execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        conn().commit()


def list_admins() -> List[sqlite3.Row]:
    return conn().execute("SELECT * FROM admins ORDER BY added_at").fetchall()


def is_admin(user_id: int) -> bool:
    if user_id in config.ADMINS:
        return True
    row = conn().execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone()
    return row is not None


def add_channel(owner_id: int, chat_id: str, title: str = "") -> int:
    with _lock:
        cur = conn().execute(
            "INSERT OR IGNORE INTO channels (owner_id, chat_id, title) VALUES (?,?,?)",
            (owner_id, chat_id, title),
        )
        conn().commit()
    if cur.lastrowid:
        return cur.lastrowid
    row = conn().execute(
        "SELECT id FROM channels WHERE owner_id=? AND chat_id=?", (owner_id, chat_id)
    ).fetchone()
    return row["id"]


def set_channel_logo(channel_id: int, logo_path: str) -> None:
    with _lock:
        conn().execute("UPDATE channels SET logo_path=? WHERE id=?", (logo_path, channel_id))
        conn().commit()


def delete_channel(channel_id: int, owner_id: int) -> None:
    with _lock:
        conn().execute("DELETE FROM channels WHERE id=? AND owner_id=?", (channel_id, owner_id))
        conn().commit()


def list_channels(owner_id: int) -> List[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM channels WHERE owner_id=? ORDER BY id", (owner_id,)
    ).fetchall()


def get_channel(channel_id: int) -> Optional[sqlite3.Row]:
    return conn().execute("SELECT * FROM channels WHERE id=?", (channel_id,)).fetchone()


def get_settings(owner_id: int) -> Dict[str, Any]:
    data = dict(config.DEFAULTS)
    rows = conn().execute("SELECT key, value FROM settings WHERE owner_id=?", (owner_id,)).fetchall()
    for r in rows:
        key, value = r["key"], r["value"]
        if key in config.BOOL_KEYS or key in config.INT_KEYS:
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
        data[key] = value
    return data


def set_setting(owner_id: int, key: str, value: Any) -> None:
    with _lock:
        conn().execute(
            "INSERT OR REPLACE INTO settings (owner_id, key, value) VALUES (?,?,?)",
            (owner_id, key, str(value)),
        )
        conn().commit()


def toggle_setting(owner_id: int, key: str) -> int:
    current = int(get_settings(owner_id).get(key, 1))
    new = 0 if current else 1
    set_setting(owner_id, key, new)
    return new


def reset_settings(owner_id: int) -> None:
    with _lock:
        conn().execute("DELETE FROM settings WHERE owner_id=?", (owner_id,))
        conn().commit()


def set_state(user_id: int, state: str = "", payload: str = "") -> None:
    with _lock:
        conn().execute(
            "INSERT OR REPLACE INTO states (user_id, state, payload) VALUES (?,?,?)",
            (user_id, state, payload),
        )
        conn().commit()


def get_state(user_id: int):
    row = conn().execute("SELECT state, payload FROM states WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return "", ""
    return row["state"] or "", row["payload"] or ""


def clear_state(user_id: int) -> None:
    set_state(user_id, "", "")
