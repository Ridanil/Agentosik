"""
Сохранение финальных результатов (п.9, п.13 ТЗ).
Ссылка на сообщение берётся ИСКЛЮЧИТЕЛЬНО из данных, собранных Telethon
(message.message_url), а не генерируется моделью.
"""
from datetime import datetime

from ai.schemas import AnalysisResult
from database import repository
from database.models import Message, ResultRecord
from utils.logger import get_logger

logger = get_logger(__name__)


async def save_results(
    search_id: int, analyzed: list[tuple[Message, AnalysisResult]]
) -> list[dict]:
    saved = []
    for message, analysis in analyzed:
        record = ResultRecord(
            search_id=search_id,
            message_id=message.id,
            relevance=analysis.relevance_score,
            quote=analysis.quote,
            explanation=analysis.explanation,
            created_at=datetime.now(),
        )
        await repository.save_result(record)
        saved.append(
            {
                "channel_username": None,  # заполняется в handler'е из join
                "message_url": message.message_url,  # реальная ссылка, не от AI
                "message_date": message.message_date,
                "quote": analysis.quote,
                "explanation": analysis.explanation,
                "relevance_score": analysis.relevance_score,
                "confidence": analysis.confidence,
            }
        )
    logger.info("Сохранено результатов: %d (search_id=%s)", len(saved), search_id)
    return saved
