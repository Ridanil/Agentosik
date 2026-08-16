"""
Управление каналами. Работает ТОЛЬКО с каналами, к которым у текущего
Telegram-аккаунта уже есть законный доступ (п.4, п.18 ТЗ):
- публичные каналы (доступны всем);
- приватные каналы, в которых аккаунт уже состоит.
Никаких попыток вступить в закрытые каналы в обход или получить доступ
к чужим приватным данным.
"""
from telethon.errors import ChannelPrivateError, UsernameNotOccupiedError
from telethon.tl.types import Channel

from collector.telegram_client import get_client
from database import repository
from database.models import Source
from utils.logger import get_logger

logger = get_logger(__name__)


class ChannelAccessError(Exception):
    """Канал недоступен текущему аккаунту (приватный / не существует)."""


async def add_channel(username: str) -> Source:
    username = username.lstrip("@").strip()
    client = get_client()
    try:
        entity = await client.get_entity(username)
    except (ChannelPrivateError,) as e:
        raise ChannelAccessError(
            f"Канал @{username} приватный, и аккаунт не имеет к нему доступа."
        ) from e
    except UsernameNotOccupiedError as e:
        raise ChannelAccessError(f"Канал @{username} не найден.") from e
    except ValueError as e:
        raise ChannelAccessError(f"Не удалось разрешить @{username}: {e}") from e

    if not isinstance(entity, Channel):
        raise ChannelAccessError(f"@{username} — не канал (это чат или пользователь).")

    source = await repository.add_source(
        username=username,
        telegram_id=entity.id,
        title=entity.title,
    )
    logger.info("Канал добавлен: @%s (%s)", username, entity.title)
    return source


async def remove_channel(username: str) -> bool:
    return await repository.remove_source(username)


async def toggle_channel(username: str, enabled: bool) -> bool:
    return await repository.set_source_enabled(username, enabled)


async def list_channels():
    return await repository.list_sources()
