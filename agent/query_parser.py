"""
Разбор запроса на естественном языке в структурированные параметры (п.10 ТЗ).
Если AI вернул невалидный JSON — один retry, затем безопасный fallback
(весь запрос целиком становится ключевым словом, чтобы поиск не сломался).
"""
import json
from datetime import date

from pydantic import ValidationError

from ai.prompts import QUERY_PARSER_SYSTEM_PROMPT, build_query_parse_prompt
from ai.provider import AIProvider
from ai.schemas import ParsedQuery
from utils.logger import get_logger

logger = get_logger(__name__)


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


async def parse_query(ai: AIProvider, user_query: str) -> ParsedQuery:
    today_iso = date.today().isoformat()
    prompt = build_query_parse_prompt(user_query, today_iso)

    for attempt in range(2):
        try:
            raw = await ai.generate_json(QUERY_PARSER_SYSTEM_PROMPT, prompt)
            cleaned = _extract_json(raw)
            data = json.loads(cleaned)
            return ParsedQuery(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Попытка %d: не удалось разобрать JSON от AI (query_parser): %s", attempt + 1, e)

    logger.warning("Fallback: использую исходный запрос как ключевое слово без разбора AI.")
    return ParsedQuery(
        keywords=[user_query],
        semantic_criteria=user_query,
        extraction_goal=user_query,
    )
