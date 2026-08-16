"""
Единая настройка логирования для всех модулей проекта.
ВАЖНО: сюда никогда не передавать значения секретов (API_HASH, BOT_TOKEN, session-строки).
"""
import logging
import sys
from logging.handlers import RotatingFileHandler

from config.settings import settings


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # уже настроен

    logger.setLevel(settings.log_level.upper())
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        settings.log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
