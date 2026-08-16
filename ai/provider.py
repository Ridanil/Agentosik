"""
Абстрактный интерфейс AI-провайдера. Приложение никогда не обращается
к Ollama напрямую — только через этот интерфейс. Это позволяет в будущем
заменить Qwen3 8B на 14B или другую модель/провайдера без изменений
в agent/ (п.2 ТЗ).
"""
from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        """Возвращает сырой текстовый ответ модели (ожидается JSON)."""
        raise NotImplementedError
