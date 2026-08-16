"""
Обёртка над Telethon client. Отдельная session-файл (п.5 ТЗ),
credentials только из .env, никогда не хардкодятся.
"""
from telethon import TelegramClient

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_client: TelegramClient | None = None


def get_client() -> TelegramClient:
    global _client
    if _client is None:
        # session-файл сохранится как <telegram_session>.session рядом с main.py
        _client = TelegramClient(
            settings.telegram_session,
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )
    return _client


async def start_client() -> TelegramClient:
    client = get_client()
    await client.start()
    me = await client.get_me()
    logger.info("Telethon подключён как: %s (id=%s)", me.username or me.first_name, me.id)
    return client
