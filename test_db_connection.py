"""Bite 1B — Test PostgreSQL connection to Supabase."""
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def test_connection():
    if not DATABASE_URL:
        raise EnvironmentError("DATABASE_URL is missing from .env — follow supabase_setup.md")

    print("Connecting to Supabase...")
    conn = await asyncpg.connect(DATABASE_URL)

    version = await conn.fetchval("SELECT version();")
    print(f"Connected! PostgreSQL version:\n{version}\n")

    # Check pgvector
    ext = await conn.fetchval(
        "SELECT extname FROM pg_extension WHERE extname = 'vector';"
    )
    if ext:
        print("pgvector extension: ENABLED")
    else:
        print("pgvector extension: NOT ENABLED — run: CREATE EXTENSION IF NOT EXISTS vector;")

    await conn.close()
    print("\nConnection test passed.")


if __name__ == "__main__":
    asyncio.run(test_connection())
