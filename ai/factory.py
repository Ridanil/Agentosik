"""
Фабрика AI-провайдера. Единственное место, где решается, какой бэкенд
использовать (п.2 ТЗ — приложение не привязано к конкретной модели/провайдеру).
Переключение — через AI_BACKEND в .env, без изменений в остальном коде.
"""
from ai.provider import AIProvider
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def get_ai_provider() -> AIProvider:
    backend = settings.ai_backend.lower().strip()

    if backend == "lmstudio":
        from ai.lmstudio import LMStudioProvider
        logger.info("AI backend: LM Studio (%s, модель %s)", settings.lmstudio_host, settings.lmstudio_model)
        return LMStudioProvider()

    if backend == "ollama":
        from ai.ollama import OllamaProvider
        logger.info("AI backend: Ollama (%s, модель %s)", settings.ollama_host, settings.ollama_model)
        return OllamaProvider()

    raise ValueError(
        f"Неизвестный AI_BACKEND='{backend}'. Допустимые значения: 'ollama', 'lmstudio'."
    )
