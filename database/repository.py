"""
Слой доступа к данным. Все запросы к SQLite идут только отсюда —
это упрощает будущий переход на embeddings/vector search (п.6, п.22 ТЗ).
"""
from __future__ import annotations

from typing import Optional

from database.database import get_connection
from database.models import Message, ResultRecord, SearchRecord, Source, now_iso
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------- sources ----------

async def add_source(username: str, telegram_id: Optional[int], title: Optional[str]) -> Source:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """INSERT INTO sources (telegram_id, username, title, enabled, added_at, last_message_id)
               VALUES (?, ?, ?, 1, ?, 0)
               ON CONFLICT(username) DO UPDATE SET enabled=1, title=excluded.title
               RETURNING *""",
            (telegram_id, username.lstrip("@"), title, now_iso()),
        )
        row = await cur.fetchone()
        await conn.commit()
        logger.info("Источник добавлен/обновлён: @%s", username)
        return Source.from_row(row)
    finally:
        await conn.close()


async def remove_source(username: str) -> bool:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "DELETE FROM sources WHERE username = ?", (username.lstrip("@"),)
        )
        await conn.commit()
        return cur.rowcount > 0
    finally:
        await conn.close()


async def set_source_enabled(username: str, enabled: bool) -> bool:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "UPDATE sources SET enabled = ? WHERE username = ?",
            (int(enabled), username.lstrip("@")),
        )
        await conn.commit()
        return cur.rowcount > 0
    finally:
        await conn.close()


async def list_sources(enabled_only: bool = False) -> list[Source]:
    conn = await get_connection()
    try:
        query = "SELECT * FROM sources"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY added_at DESC"
        cur = await conn.execute(query)
        rows = await cur.fetchall()
        return [Source.from_row(r) for r in rows]
    finally:
        await conn.close()


async def update_scan_progress(source_id: int, last_message_id: int) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE sources SET last_message_id = ?, last_scan_at = ? WHERE id = ?",
            (last_message_id, now_iso(), source_id),
        )
        await conn.commit()
    finally:
        await conn.close()


# ---------- messages ----------

async def save_message(msg: Message) -> Optional[int]:
    """Возвращает id вставленной строки, либо None если уже существовала (дубликат)."""
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """INSERT OR IGNORE INTO messages
               (source_id, telegram_message_id, message_date, author, text,
                message_url, media_type, collected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                msg.source_id, msg.telegram_message_id, msg.message_date, msg.author,
                msg.text, msg.message_url, msg.media_type, msg.collected_at,
            ),
        )
        await conn.commit()
        return cur.lastrowid if cur.rowcount > 0 else None
    finally:
        await conn.close()


async def search_messages_by_keywords(
    keywords: list[str],
    source_ids: Optional[list[int]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 500,
) -> list[Message]:
    """Уровень 1: обычный текстовый поиск (LIKE + лемматизированные варианты слов)."""
    conn = await get_connection()
    try:
        conditions = []
        params: list = []

        if keywords:
            kw_conditions = []
            for kw in keywords:
                kw_conditions.append("text LIKE ?")
                params.append(f"%{kw}%")
            conditions.append("(" + " OR ".join(kw_conditions) + ")")

        if source_ids:
            placeholders = ",".join("?" * len(source_ids))
            conditions.append(f"source_id IN ({placeholders})")
            params.extend(source_ids)

        if date_from:
            conditions.append("message_date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("message_date <= ?")
            params.append(date_to)

        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM messages WHERE {where} ORDER BY message_date DESC LIMIT ?"
        params.append(limit)

        cur = await conn.execute(query, params)
        rows = await cur.fetchall()
        return [Message.from_row(r) for r in rows]
    finally:
        await conn.close()


async def get_source_by_username(username: str) -> Optional[Source]:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "SELECT * FROM sources WHERE username = ?", (username.lstrip("@"),)
        )
        row = await cur.fetchone()
        return Source.from_row(row) if row else None
    finally:
        await conn.close()


# ---------- searches / results ----------

async def create_search(query: str, date_from: Optional[str], date_to: Optional[str]) -> int:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "INSERT INTO searches (query, created_at, date_from, date_to) VALUES (?, ?, ?, ?)",
            (query, now_iso(), date_from, date_to),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def save_result(result: ResultRecord) -> int:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """INSERT INTO results (search_id, message_id, relevance, quote, explanation, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (result.search_id, result.message_id, result.relevance,
             result.quote, result.explanation, now_iso()),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def get_latest_results(limit: int = 10) -> list[dict]:
    conn = await get_connection()
    try:
        cur = await conn.execute(
            """SELECT r.*, m.text AS message_text, m.message_url, m.message_date,
                      s.username AS source_username, se.query AS search_query
               FROM results r
               JOIN messages m ON m.id = r.message_id
               JOIN sources s ON s.id = m.source_id
               JOIN searches se ON se.id = r.search_id
               ORDER BY r.created_at DESC LIMIT ?""",
            (limit,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()
