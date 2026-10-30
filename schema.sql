-- SQLite schema — created automatically on startup by db.get_pool()

-- Companies: each business using the platform
CREATE TABLE IF NOT EXISTS companies (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT NOT NULL,
    api_key              TEXT UNIQUE NOT NULL,
    knowledge_base       TEXT,                          -- plain text: FAQs, products, policies
    welcome_message      TEXT DEFAULT 'أهلاً! كيف أقدر أساعدك؟',
    language             TEXT NOT NULL DEFAULT 'ar',
    messenger_page_id    TEXT,         -- Facebook page ID after OAuth connect
    messenger_page_token TEXT,         -- Facebook page access token after OAuth connect
    created_at           TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Users: people who message the bot
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT,
    phone       TEXT UNIQUE,           -- WhatsApp number e.g. "201012345678"
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Conversations: one per chat session per platform
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id  INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    platform    TEXT NOT NULL CHECK (platform IN ('whatsapp', 'messenger', 'web', 'test')),
    started_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed'))
);

-- Messages: every message in a conversation
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'bot')),
    content         TEXT NOT NULL,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id    ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
