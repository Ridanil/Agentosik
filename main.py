"""
Точка входа. Запускает Telethon Collector и aiogram Bot как независимые
asyncio-таски в одном процессе (проще для Windows, чем управлять двумя
процессами через .bat). Падение одной таски логируется и не должно
приводить к незаметному краху всего приложения.
"""
import asyncio

from aiogram import Bot, Dispatcher

from bot.handlers import channels, common, results, search
from collector.message_collector import run_periodic_collector
from collector.telegram_client import start_client
from config.settings import settings
from database.database import init_db
from utils.logger import get_logger

logger = get_logger("main")


async def run_bot():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(common.router)
    dp.include_router(channels.router)
    dp.include_router(search.router)
    dp.include_router(results.router)

    logger.info("Telegram-бот запускается...")
    await dp.start_polling(bot)


async def run_collector():
    await start_client()
    await run_periodic_collector(interval_seconds=300)


async def main():
    logger.info("Инициализация базы данных...")
    await init_db()

    logger.info("Запуск Collector и Bot параллельно...")
    tasks = [
        asyncio.create_task(run_collector(), name="collector"),
        asyncio.create_task(run_bot(), name="bot"),
    ]

    try:
        await asyncio.gather(*tasks)
    except Exception:
        logger.exception("Критическая ошибка в основном цикле")
        for t in tasks:
            t.cancel()
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем.")
