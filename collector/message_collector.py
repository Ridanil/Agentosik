"""
Сбор сообщений (п.5 ТЗ).
- Не создаёт дубликаты: UNIQUE(source_id, telegram_message_id) в БД + запоминание last_message_id.
- Корректно восстанавливается после перезапуска: продолжает с last_message_id.
- Уважает FloodWait от Telegram (не обходит ограничения, просто ждёт).
- После сбора считает эмбеддинги для новых сообщений — retrieval-часть RAG (п.6 ТЗ).
"""
import asyncio

from telethon.errors import FloodWaitError

from agent.embeddings import EMBEDDING_MODEL_NAME, embed_texts, vector_to_blob
from collector.telegram_client import get_client
from database import repository
from database.models import Message, now_iso
from utils.logger import get_logger

logger = get_logger(__name__)


def build_message_url(username: str, telegram_message_id: int) -> str:
    return f"https://t.me/{username}/{telegram_message_id}"


async def _persist_message(source_id: int, username: str, tg_msg) -> bool:
    if not tg_msg.text and not tg_msg.message:
        text = tg_msg.raw_text or ""
    else:
        text = tg_msg.text or tg_msg.message or ""

    media_type = None
    if tg_msg.media:
        media_type = type(tg_msg.media).__name__

    author = None
    if tg_msg.sender:
        author = getattr(tg_msg.sender, "username", None) or getattr(tg_msg.sender, "title", None)

    msg = Message(
        source_id=source_id,
        telegram_message_id=tg_msg.id,
        message_date=tg_msg.date.isoformat() if tg_msg.date else None,
        author=author,
        text=text,
        message_url=build_message_url(username, tg_msg.id),
        media_type=media_type,
        collected_at=now_iso(),
    )
    inserted_id = await repository.save_message(msg)
    return inserted_id is not None


async def collect_source_history(source, limit_per_run: int = 500) -> int:
    """
    Загружает сообщения канала начиная с last_message_id (или с начала истории,
    если сбор ранее не запускался). Возвращает количество новых сохранённых сообщений.
    """
    client = get_client()
    new_count = 0
    max_id_seen = source.last_message_id

    try:
        # min_id гарантирует, что мы не тянем повторно уже собранные сообщения
        async for tg_msg in client.iter_messages(
            source.username, min_id=source.last_message_id, limit=limit_per_run, reverse=False
        ):
            saved = await _persist_message(source.id, source.username, tg_msg)
            if saved:
                new_count += 1
            if tg_msg.id > max_id_seen:
                max_id_seen = tg_msg.id

    except FloodWaitError as e:
        logger.warning(
            "FloodWait от Telegram для @%s: нужно подождать %s секунд. "
            "Прерываю сбор для этого канала, продолжу в следующем цикле.",
            source.username, e.seconds,
        )
        await asyncio.sleep(min(e.seconds, 300))  # не ждём вечность в рамках одного цикла

    if max_id_seen > source.last_message_id:
        await repository.update_scan_progress(source.id, max_id_seen)

    logger.info("Канал @%s: собрано новых сообщений %d", source.username, new_count)
    return new_count


async def embed_pending_messages(batch_size: int = 100) -> int:
    """Считает эмбеддинги для сообщений, у которых их ещё нет — RAG retrieval-индекс
    (п.6, п.22 ТЗ). Батчируется по той же причине, что и AI-анализ (п.11 ТЗ):
    не перегружать локальную модель. Идемпотентна: безопасно перезапускать,
    в том числе после сбоя процесса — просто продолжит с необработанных сообщений."""
    total = 0
    while True:
        pending = await repository.get_messages_without_embeddings(limit=batch_size)
        if not pending:
            break
        texts = [msg.text or "" for msg in pending]
        vectors = await embed_texts(texts)
        for msg, vec in zip(pending, vectors):
            await repository.save_embedding(msg.id, vector_to_blob(vec), EMBEDDING_MODEL_NAME)
        total += len(pending)

    if total:
        logger.info("Посчитаны эмбеддинги для %d новых сообщений", total)
    return total


async def collect_all_enabled_sources() -> dict:
    """Проходит по всем включённым каналам, собирает новые сообщения,
    затем досчитывает эмбеддинги для всего нового за один проход (эффективнее,
    чем пересчитывать по каждому каналу отдельно)."""
    sources = await repository.list_sources(enabled_only=True)
    summary = {}
    for source in sources:
        try:
            count = await collect_source_history(source)
            summary[source.username] = count
        except Exception:
            logger.exception("Ошибка сбора для канала @%s", source.username)
            summary[source.username] = "error"

    try:
        await embed_pending_messages()
    except Exception:
        logger.exception("Ошибка при подсчёте эмбеддингов")

    return summary


async def run_periodic_collector(interval_seconds: int = 300):
    """Фоновый цикл сбора новых сообщений (используется в main.py как asyncio-таска)."""
    while True:
        logger.info("Запуск цикла сбора сообщений...")
        try:
            summary = await collect_all_enabled_sources()
            logger.info("Итог цикла сбора: %s", summary)
        except Exception:
            logger.exception("Ошибка в цикле сбора сообщений")
        await asyncio.sleep(interval_seconds)
