"""Database layer — single SQLite file, no external service.

Every function keeps the async signature the rest of the app uses; the
blocking sqlite3 calls run in a worker thread. WAL mode lets the web,
WhatsApp and admin routes read while one of them writes.
"""
import asyncio
import os
import sqlite3
import uuid
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "nilechat.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _run(fn, *args):
    def work():
        conn = _connect()
        try:
            result = fn(conn, *args)
            conn.commit()
            return result
        finally:
            conn.close()
    return asyncio.to_thread(work)


def _init(conn):
    conn.execute("PRAGMA journal_mode = WAL")
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())


async def get_pool():
    """Create the database file and tables if missing (called on app startup)."""
    await _run(_init)


async def close_pool():
    pass


async def get_or_create_user(phone: str, name: str = None) -> int:
    def q(conn):
        row = conn.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
        if row:
            return row["id"]
        return conn.execute(
            "INSERT INTO users (phone, name) VALUES (?, ?)", (phone, name)
        ).lastrowid
    return await _run(q)


async def get_or_create_conversation(user_id: int, platform: str, company_id: int = None) -> int:
    def q(conn):
        row = conn.execute(
            """SELECT id FROM conversations
               WHERE user_id = ? AND platform = ? AND status = 'active'
               AND company_id IS ?
               ORDER BY started_at DESC, id DESC LIMIT 1""",
            (user_id, platform, company_id),
        ).fetchone()
        if row:
            return row["id"]
        return conn.execute(
            "INSERT INTO conversations (user_id, platform, company_id) VALUES (?, ?, ?)",
            (user_id, platform, company_id),
        ).lastrowid
    return await _run(q)


async def save_message(conversation_id: int, role: str, content: str) -> int:
    def q(conn):
        return conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        ).lastrowid
    return await _run(q)


async def get_recent_messages(conversation_id: int, limit: int = 5) -> list[dict]:
    def q(conn):
        rows = conn.execute(
            """SELECT role, content FROM (
                   SELECT role, content, id
                   FROM messages
                   WHERE conversation_id = ?
                   ORDER BY id DESC
                   LIMIT ?
               ) sub ORDER BY id ASC""",
            (conversation_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    return await _run(q)


# ── Company / SaaS functions ──────────────────────────────────────────────────

async def get_company_by_api_key(api_key: str) -> dict | None:
    def q(conn):
        row = conn.execute(
            "SELECT id, name, knowledge_base, welcome_message, language FROM companies WHERE api_key = ?",
            (api_key,),
        ).fetchone()
        return dict(row) if row else None
    return await _run(q)


async def get_company_by_id(company_id: int) -> dict | None:
    def q(conn):
        row = conn.execute(
            "SELECT id, name, api_key, knowledge_base, welcome_message, language FROM companies WHERE id = ?",
            (company_id,),
        ).fetchone()
        return dict(row) if row else None
    return await _run(q)


async def create_company(name: str, knowledge_base: str = None, welcome_message: str = None) -> dict:
    def q(conn):
        api_key = str(uuid.uuid4())
        company_id = conn.execute(
            "INSERT INTO companies (name, api_key, knowledge_base, welcome_message) VALUES (?, ?, ?, ?)",
            (name, api_key, knowledge_base, welcome_message or "أهلاً! كيف أقدر أساعدك؟"),
        ).lastrowid
        return {"id": company_id, "name": name, "api_key": api_key}
    return await _run(q)


async def update_company_knowledge(company_id: int, knowledge_base: str, welcome_message: str = None) -> bool:
    def q(conn):
        if welcome_message:
            conn.execute(
                "UPDATE companies SET knowledge_base = ?, welcome_message = ? WHERE id = ?",
                (knowledge_base, welcome_message, company_id),
            )
        else:
            conn.execute(
                "UPDATE companies SET knowledge_base = ? WHERE id = ?",
                (knowledge_base, company_id),
            )
        return True
    return await _run(q)


async def set_company_messenger(api_key: str, page_id: str, page_token: str) -> None:
    def q(conn):
        conn.execute(
            "UPDATE companies SET messenger_page_id = ?, messenger_page_token = ? WHERE api_key = ?",
            (page_id, page_token, api_key),
        )
    await _run(q)


async def get_company_by_messenger_page_id(page_id: str) -> dict | None:
    def q(conn):
        row = conn.execute(
            """SELECT id, name, knowledge_base, welcome_message, language,
                      messenger_page_id, messenger_page_token
               FROM companies WHERE messenger_page_id = ?""",
            (page_id,),
        ).fetchone()
        return dict(row) if row else None
    return await _run(q)


async def list_companies() -> list[dict]:
    def q(conn):
        rows = conn.execute(
            "SELECT id, name, api_key, welcome_message, created_at FROM companies ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    return await _run(q)
