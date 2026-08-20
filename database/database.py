"""
Подключение к SQLite. WAL-режим обязателен: Collector (Telethon) и Bot (aiogram)
работают как два независимых процесса и пишут в БД одновременно.
Без WAL это приводит к 'database is locked'.
"""
import aiosqlite

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT UNIQUE,
    title TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    added_at TEXT NOT NULL,
    last_message_id INTEGER DEFAULT 0,
    last_scan_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    telegram_message_id INTEGER NOT NULL,
    message_date TEXT,
    author TEXT,
    text TEXT,
    message_url TEXT,
    media_type TEXT,
    collected_at TEXT NOT NULL,
    UNIQUE(source_id, telegram_message_id)
);
CREATE INDEX IF NOT EXISTS idx_messages_text ON messages(text);
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(message_date);
CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source_id);

CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    created_at TEXT NOT NULL,
    date_from TEXT,
    date_to TEXT
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id INTEGER NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    relevance REAL,
    quote TEXT,
    explanation TEXT,
    created_at TEXT NOT NULL
);

-- RAG (п.6, п.22 ТЗ): эмбеддинги сообщений для семантического (векторного) поиска.
-- Один эмбеддинг на сообщение, пересчитывается при смене модели (ON CONFLICT в repository.py).
CREATE TABLE IF NOT EXISTS message_embeddings (
    message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    embedding BLOB NOT NULL,
    model_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


async def get_connection() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(settings.database_path, timeout=30)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA busy_timeout=5000;")
    await conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db() -> None:
    conn = await get_connection()
    try:
        await conn.executescript(SCHEMA)
        await conn.commit()
        logger.info("База данных инициализирована: %s", settings.database_path)
    finally:
        await conn.close()
