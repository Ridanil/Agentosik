"""
Централизованная конфигурация. Все секреты берутся только из .env,
никогда не хардкодятся и не логируются.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telethon (user account)
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session: str = "collector_session"

    # aiogram (bot)
    bot_token: str

    # Database
    database_path: str = "./data/agent.db"

    # AI backend: "ollama" или "lmstudio"
    ai_backend: str = "lmstudio"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    ollama_timeout_seconds: int = 120

    # LM Studio (OpenAI-совместимый API)
    lmstudio_host: str = "http://localhost:1234/v1"
    lmstudio_model: str = "qwen3-8b"

    max_messages_per_ai_batch: int = 10

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/agent.log"

    def ensure_dirs(self) -> None:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
