"""
memory/store.py — SQLite backend for Jarvis memory.

Schema version is stored in the DB so future migrations can be applied
automatically on startup without manual intervention.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional

DB_PATH       = os.path.join("data", "jarvis.db")
SCHEMA_VERSION = 2   # bump when schema changes


def _conn() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db() -> None:
    """Create / migrate tables on startup. Safe to call every time."""
    with _conn() as con:
        # Schema-version tracking table
        con.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            )
        """)
        row = con.execute("SELECT version FROM schema_version").fetchone()
        current = row["version"] if row else 0

        if current < 1:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT    NOT NULL,
                    role       TEXT    NOT NULL CHECK(role IN ('user','assistant')),
                    content    TEXT    NOT NULL,
                    ts         TEXT    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conv_session
                    ON conversations(session_id, id);

                CREATE TABLE IF NOT EXISTS facts (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    key        TEXT    NOT NULL,
                    value      TEXT    NOT NULL,
                    confidence REAL    NOT NULL DEFAULT 1.0,
                    source     TEXT,
                    ts         TEXT    NOT NULL,
                    UNIQUE(key)
                );
            """)

        if current < 2:
            # v2: add soft-delete flag to facts
            try:
                con.execute("ALTER TABLE facts ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass   # column already exists (idempotent)

        if row:
            con.execute("UPDATE schema_version SET version=?", (SCHEMA_VERSION,))
        else:
            con.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))


# ── Conversations ────────────────────────────────────────────────────────────

def save_turn(session_id: str, role: str, content: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO conversations (session_id, role, content, ts) VALUES (?,?,?,?)",
            (session_id, role, content, datetime.utcnow().isoformat()),
        )


def get_recent_turns(n: int = 30) -> list[dict]:
    """Return last n turns (oldest first) for context seeding on startup."""
    with _conn() as con:
        rows = con.execute(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def clear_history() -> None:
    """Wipe all conversation rows — used by reset(clear_db=True)."""
    with _conn() as con:
        con.execute("DELETE FROM conversations")


def purge_old_turns(days: int = 90) -> int:
    """Delete conversation turns older than `days`. Returns rows deleted."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with _conn() as con:
        cur = con.execute("DELETE FROM conversations WHERE ts < ?", (cutoff,))
        return cur.rowcount


# ── Facts ────────────────────────────────────────────────────────────────────

def upsert_fact(key: str, value: str, confidence: float = 1.0, source: str = "") -> None:
    with _conn() as con:
        con.execute("""
            INSERT INTO facts (key, value, confidence, source, ts, deleted)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(key) DO UPDATE SET
                value      = excluded.value,
                confidence = excluded.confidence,
                source     = excluded.source,
                ts         = excluded.ts,
                deleted    = 0
        """, (key, value, confidence, source, datetime.utcnow().isoformat()))


def get_all_facts(limit: int = 30) -> list[dict]:
    """Return active facts, highest confidence first."""
    with _conn() as con:
        rows = con.execute(
            "SELECT key, value, confidence FROM facts "
            "WHERE deleted=0 ORDER BY confidence DESC, ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"key": r["key"], "value": r["value"], "confidence": r["confidence"]} for r in rows]


def delete_fact(key: str) -> None:
    """Soft-delete a fact by key."""
    with _conn() as con:
        con.execute("UPDATE facts SET deleted=1 WHERE key=?", (key,))


def hard_delete_all_facts() -> int:
    """Permanently remove all facts. Used by forget_all."""
    with _conn() as con:
        cur = con.execute("DELETE FROM facts")
        return cur.rowcount


def search_facts(query: str) -> list[dict]:
    q = f"%{query.lower()}%"
    with _conn() as con:
        rows = con.execute(
            "SELECT key, value, confidence FROM facts "
            "WHERE deleted=0 AND (lower(key) LIKE ? OR lower(value) LIKE ?)",
            (q, q),
        ).fetchall()
    return [{"key": r["key"], "value": r["value"], "confidence": r["confidence"]} for r in rows]