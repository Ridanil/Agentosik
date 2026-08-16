"""
Agent Core: связывает все этапы поиска в один pipeline (п.8 ТЗ):
запрос -> parse -> preliminary search -> AI analysis -> extraction -> save.
"""
from agent.analyzer import analyze_batch
from agent.extractor import save_results
from agent.query_parser import parse_query
from agent.search_engine import preliminary_search
from ai.provider import AIProvider
from database import repository
from utils.logger import get_logger

logger = get_logger(__name__)


async def run_search(ai: AIProvider, user_query: str) -> dict:
    """Полный цикл поиска. Возвращает словарь с результатами и метаданными."""
    parsed = await parse_query(ai, user_query)
    logger.info("Запрос разобран: keywords=%s, sources=%s, %s..%s",
                parsed.keywords, parsed.selected_sources, parsed.date_from, parsed.date_to)

    search_id = await repository.create_search(
        query=user_query, date_from=parsed.date_from, date_to=parsed.date_to
    )

    candidates = await preliminary_search(parsed)
    if not candidates:
        return {
            "search_id": search_id,
            "parsed": parsed,
            "candidates_count": 0,
            "results": [],
        }

    # channel labels для контекста в промпте и для отображения
    sources = await repository.list_sources()
    source_map = {s.id: s for s in sources}
    channel_labels = {sid: f"@{s.username}" for sid, s in source_map.items()}

    task = parsed.extraction_goal or user_query
    analyzed = await analyze_batch(ai, task, candidates, channel_labels)

    results = await save_results(search_id, analyzed)

    # дозаполняем channel_username из source_map (extractor его не знает)
    for res, (msg, _) in zip(results, analyzed):
        src = source_map.get(msg.source_id)
        res["channel_username"] = f"@{src.username}" if src else "неизвестно"

    return {
        "search_id": search_id,
        "parsed": parsed,
        "candidates_count": len(candidates),
        "results": results,
    }
