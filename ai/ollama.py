"""
Реализация AIProvider через локальный Ollama (п.2 ТЗ).
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from ai.provider import AIProvider
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class OllamaProvider(AIProvider):
    def __init__(self, model: str | None = None):
        self.model = model or settings.ollama_model
        self.host = settings.ollama_host.rstrip("/")
        self.timeout = settings.ollama_timeout_seconds

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    )
    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",  # Ollama форсирует валидный JSON-вывод
            "options": {"temperature": 0.1},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(f"{self.host}/api/chat", json=payload)
                resp.raise_for_status()
            except httpx.ConnectError:
                logger.error(
                    "Не удалось подключиться к Ollama на %s. Проверьте, что Ollama запущен "
                    "(команда: ollama serve) и модель %s загружена (ollama pull %s).",
                    self.host, self.model, self.model,
                )
                raise
            data = resp.json()
            return data.get("message", {}).get("content", "")
