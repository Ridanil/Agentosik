"""
Реализация AIProvider через LM Studio (локальный сервер с OpenAI-совместимым API).
Используется как альтернатива Ollama — выбирается через .env (AI_BACKEND=lmstudio),
без изменений в agent/ и остальном приложении (п.2 ТЗ).

LM Studio: Settings → Developer → Local Server → Start Server
По умолчанию слушает http://localhost:1234/v1
"""
import os

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from ai.provider import AIProvider
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class LMStudioProvider(AIProvider):
    def __init__(self, model: str | None = None):
        self.model = model or settings.lmstudio_model
        self.api_token = os.getenv("LMSTUDIO_TOKEN", "")
        self.host = settings.lmstudio_host.rstrip("/")
        self.timeout = settings.ollama_timeout_seconds  # общий таймаут для локальных LLM

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
            "temperature": 0.1,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "response_schema",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True
                    }
                }
            }
        }

        # 👇 Отладка
        logger.info(f"LM Studio request to {self.host}, model: {self.model}")
        logger.info(f"Token present: {'YES' if self.api_token else 'NO'} (length: {len(self.api_token)})")

        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.host}/chat/completions",
                    json=payload,
                    headers=headers
                )
                resp.raise_for_status()
            except httpx.ConnectError:
                logger.error(
                    "Не удалось подключиться к LM Studio на %s. Проверьте, что в LM Studio "
                    "запущен локальный сервер (Developer → Local Server → Start Server) "
                    "и загружена модель %s.",
                    self.host, self.model,
                )
                raise
            except httpx.HTTPStatusError as e:
                logger.error("LM Studio вернул ошибку %s: %s", e.response.status_code, e.response.text)
                raise

            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                logger.error("Неожиданный формат ответа от LM Studio: %s", data)
                return ""
