-- Full schema with pgvector support + SaaS multi-tenant companies
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Companies: each business using the SaaS platform
CREATE TABLE IF NOT EXISTS companies (
    id                   BIGSERIAL PRIMARY KEY,
    name                 TEXT NOT NULL,
    api_key              TEXT UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    knowledge_base       TEXT,                          -- plain text: FAQs, products, policies
    welcome_message      TEXT DEFAULT 'أهلاً! كيف أقدر أساعدك؟',
    language             TEXT NOT NULL DEFAULT 'ar',    -- ar = Arabic, en = English
    messenger_page_id    TEXT,         -- Facebook page ID after OAuth connect
    messenger_page_token TEXT,         -- Facebook page access token after OAuth connect
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Migration: add messenger columns if table already exists
ALTER TABLE companies ADD COLUMN IF NOT EXISTS messenger_page_id    TEXT;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS messenger_page_token TEXT;

-- Users: people who message the bot
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT,
    phone       TEXT UNIQUE,           -- WhatsApp number e.g. "201012345678"
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations: one per chat session per platform
CREATE TABLE IF NOT EXISTS conversations (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id  BIGINT REFERENCES companies(id) ON DELETE SET NULL,
    platform    TEXT NOT NULL CHECK (platform IN ('whatsapp', 'messenger', 'web', 'test')),
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed'))
);

-- Messages: every message in a conversation
CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'bot')),
    content         TEXT NOT NULL,
    embedding       VECTOR(384),        -- Bite 1D: semantic search column
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_conversations_user_id   ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at      ON messages(created_at);

-- Vector index for similarity search (Bite 1D)
CREATE INDEX IF NOT EXISTS idx_messages_embedding
    ON messages USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
