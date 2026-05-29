"""
memory/store.py — SQLite backend for Jarvis memory.

Interface design: every public method here is what a future ChromaStore
would also need to implement. Swap the backend by changing MemoryManager
to instantiate a different class. Nothing else changes.

Tables
------
conversations : every turn, in order, with session grouping
facts         : extracted key-value beliefs about the user / world
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join("data", "jarvis.db")


def _conn() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")   # safe for concurrent reads
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('user','assistant')),
                content     TEXT    NOT NULL,
                ts          TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conv_session
                ON conversations(session_id, id);

            CREATE TABLE IF NOT EXISTS facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                key         TEXT    NOT NULL,
                value       TEXT    NOT NULL,
                confidence  REAL    NOT NULL DEFAULT 1.0,
                source      TEXT,
                ts          TEXT    NOT NULL,
                UNIQUE(key)
            );
        """)


# ── Conversations ──────────────────────────────────────────────────────────

def save_turn(session_id: str, role: str, content: str):
    """Append one turn to the conversation log."""
    with _conn() as con:
        con.execute(
            "INSERT INTO conversations (session_id, role, content, ts) VALUES (?,?,?,?)",
            (session_id, role, content, datetime.utcnow().isoformat())
        )


def get_recent_turns(n: int = 20) -> list[dict]:
    """
    Return the last n turns across all sessions, oldest first.
    Used to rebuild context on startup.
    """
    with _conn() as con:
        rows = con.execute(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_session_turns(session_id: str) -> list[dict]:
    """Return all turns for one session (current session recovery)."""
    with _conn() as con:
        rows = con.execute(
            "SELECT role, content FROM conversations WHERE session_id=? ORDER BY id",
            (session_id,)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


# ── Facts ──────────────────────────────────────────────────────────────────

def upsert_fact(key: str, value: str, confidence: float = 1.0, source: str = ""):
    """
    Insert or update a fact. Key is the unique identifier.
    e.g. upsert_fact("user_name", "Raj")
         upsert_fact("prefers_units", "Celsius")
    """
    with _conn() as con:
        con.execute("""
            INSERT INTO facts (key, value, confidence, source, ts)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value      = excluded.value,
                confidence = excluded.confidence,
                source     = excluded.source,
                ts         = excluded.ts
        """, (key, value, confidence, source, datetime.utcnow().isoformat()))


def get_all_facts() -> list[dict]:
    """Return all facts, highest confidence first."""
    with _conn() as con:
        rows = con.execute(
            "SELECT key, value, confidence FROM facts ORDER BY confidence DESC, ts DESC"
        ).fetchall()
    return [{"key": r["key"], "value": r["value"], "confidence": r["confidence"]} for r in rows]


def delete_fact(key: str):
    """Remove a fact by key."""
    with _conn() as con:
        con.execute("DELETE FROM facts WHERE key=?", (key,))


def search_facts(query: str) -> list[dict]:
    """
    Simple substring search across keys and values.
    This is the method a ChromaStore would replace with cosine similarity.
    """
    q = f"%{query.lower()}%"
    with _conn() as con:
        rows = con.execute(
            "SELECT key, value, confidence FROM facts WHERE lower(key) LIKE ? OR lower(value) LIKE ?",
            (q, q)
        ).fetchall()
    return [{"key": r["key"], "value": r["value"], "confidence": r["confidence"]} for r in rows]