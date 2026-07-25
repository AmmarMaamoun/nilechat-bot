"""Database layer — async PostgreSQL with asyncpg."""
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise EnvironmentError("DATABASE_URL missing from .env")
        _pool = await asyncpg.create_pool(
            url,
            min_size=1,
            max_size=5,
            statement_cache_size=0,  # required for Supabase pooler
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_or_create_user(phone: str, name: str = None) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM users WHERE phone = $1", phone
        )
        if row:
            return row["id"]
        row = await conn.fetchrow(
            "INSERT INTO users (phone, name) VALUES ($1, $2) RETURNING id",
            phone, name,
        )
        return row["id"]


async def get_or_create_conversation(user_id: int, platform: str, company_id: int = None) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id FROM conversations
               WHERE user_id = $1 AND platform = $2 AND status = 'active'
               AND (company_id = $3 OR ($3 IS NULL AND company_id IS NULL))
               ORDER BY started_at DESC LIMIT 1""",
            user_id, platform, company_id,
        )
        if row:
            return row["id"]
        row = await conn.fetchrow(
            "INSERT INTO conversations (user_id, platform, company_id) VALUES ($1, $2, $3) RETURNING id",
            user_id, platform, company_id,
        )
        return row["id"]


async def save_message(conversation_id: int, role: str, content: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO messages (conversation_id, role, content)
               VALUES ($1, $2, $3) RETURNING id""",
            conversation_id, role, content,
        )
        return row["id"]


async def get_recent_messages(conversation_id: int, limit: int = 5) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT role, content FROM (
                   SELECT role, content, created_at
                   FROM messages
                   WHERE conversation_id = $1
                   ORDER BY created_at DESC
                   LIMIT $2
               ) sub ORDER BY created_at ASC""",
            conversation_id, limit,
        )
        return [dict(r) for r in rows]


# ── Company / SaaS functions ──────────────────────────────────────────────────

async def get_company_by_api_key(api_key: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, knowledge_base, welcome_message, language FROM companies WHERE api_key = $1",
            api_key,
        )
        return dict(row) if row else None


async def get_company_by_id(company_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, api_key, knowledge_base, welcome_message, language FROM companies WHERE id = $1",
            company_id,
        )
        return dict(row) if row else None


async def create_company(name: str, knowledge_base: str = None, welcome_message: str = None) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO companies (name, knowledge_base, welcome_message)
               VALUES ($1, $2, $3) RETURNING id, name, api_key""",
            name,
            knowledge_base,
            welcome_message or "أهلاً! كيف أقدر أساعدك؟",
        )
        return dict(row)


async def update_company_knowledge(company_id: int, knowledge_base: str, welcome_message: str = None) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if welcome_message:
            await conn.execute(
                "UPDATE companies SET knowledge_base = $1, welcome_message = $2 WHERE id = $3",
                knowledge_base, welcome_message, company_id,
            )
        else:
            await conn.execute(
                "UPDATE companies SET knowledge_base = $1 WHERE id = $2",
                knowledge_base, company_id,
            )
        return True


async def get_company_by_messenger_page_id(page_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, name, knowledge_base, welcome_message, language,
                      messenger_page_id, messenger_page_token
               FROM companies WHERE messenger_page_id = $1""",
            page_id,
        )
        return dict(row) if row else None


async def list_companies() -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, api_key, welcome_message, created_at FROM companies ORDER BY created_at DESC"
        )
        return [dict(r) for r in rows]
