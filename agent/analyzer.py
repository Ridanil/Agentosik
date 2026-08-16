"""
Уровень 2 поиска (п.7, п.9 ТЗ): AI semantic analysis каждого кандидата сообщения.
Батчируется, чтобы не перегружать локальную модель (п.11 ТЗ) — контролируется
MAX_MESSAGES_PER_AI_BATCH.
"""
import json

from pydantic import ValidationError

from ai.prompts import ANALYZER_SYSTEM_PROMPT, build_analysis_user_prompt
from ai.provider import AIProvider
from ai.schemas import AnalysisResult
from config.settings import settings
from database.models import Message
from utils.logger import get_logger

logger = get_logger(__name__)


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


async def analyze_message(
    ai: AIProvider, task: str, message: Message, channel_label: str
) -> AnalysisResult | None:
    """Возвращает None, если AI не смог дать валидный ответ после retry —
    такое сообщение НЕ попадает в результаты (лучше пропустить, чем придумать)."""
    prompt = build_analysis_user_prompt(
        task=task,
        message_text=message.text or "",
        channel=channel_label,
        date=message.message_date or "неизвестна",
    )

    for attempt in range(2):
        try:
            raw = await ai.generate_json(ANALYZER_SYSTEM_PROMPT, prompt)
            cleaned = _extract_json(raw)
            data = json.loads(cleaned)
            result = AnalysisResult(**data)

            # Дополнительная защита: если модель не нашла формулировку,
            # но при этом заявила relevant=true с несуществующей цитатой — не доверяем.
            if result.quote != "точная формулировка отсутствует" and result.quote not in (message.text or ""):
                logger.warning(
                    "Цитата от AI не найдена дословно в исходном тексте (message_id=%s). "
                    "Отклоняю результат как потенциальную галлюцинацию.", message.id,
                )
                return None

            return result
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(
                "Попытка %d: невалидный JSON от AI при анализе message_id=%s: %s",
                attempt + 1, message.id, e,
            )

    logger.error("Не удалось получить валидный анализ для message_id=%s, пропускаю.", message.id)
    return None


async def analyze_batch(
    ai: AIProvider, task: str, messages: list[Message], channel_labels: dict[int, str]
) -> list[tuple[Message, AnalysisResult]]:
    batch = messages[: settings.max_messages_per_ai_batch]
    if len(messages) > settings.max_messages_per_ai_batch:
        logger.info(
            "Кандидатов больше лимита (%d > %d), анализирую только первые %d "
            "(экономия ресурсов, п.11 ТЗ).",
            len(messages), settings.max_messages_per_ai_batch, settings.max_messages_per_ai_batch,
        )

    results = []
    for msg in batch:
        label = channel_labels.get(msg.source_id, "неизвестный канал")
        analysis = await analyze_message(ai, task, msg, label)
        if analysis and analysis.relevant:
            results.append((msg, analysis))
    return results
