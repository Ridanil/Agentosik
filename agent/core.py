"""
Agent Core: связывает все этапы поиска в один pipeline (п.8 ТЗ):
запрос -> parse -> preliminary search (лексический + семантический/RAG) ->
AI analysis -> extraction -> save.
"""
from agent.analyzer import analyze_batch
from agent.extractor import save_results
from agent.query_parser import parse_query
from agent.search_engine import preliminary_search
from agent.semantic_search import semantic_search
from ai.provider import AIProvider
from database import repository
from database.models import Message
from utils.logger import get_logger

logger = get_logger(__name__)


def _merge_candidates(*groups: list[Message]) -> list[Message]:
    """Объединяет кандидатов из разных источников поиска (лексика + смысл),
    убирая дубликаты по id. Порядок первого появления сохраняется, т.е.
    лексические совпадения (более точные) идут первыми."""
    seen: set[int] = set()
    merged: list[Message] = []
    for group in groups:
        for msg in group:
            if msg.id not in seen:
                seen.add(msg.id)
                merged.append(msg)
    return merged


async def run_search(ai: AIProvider, user_query: str) -> dict:
    """Полный цикл поиска. Возвращает словарь с результатами и метаданными."""
    parsed = await parse_query(ai, user_query)
    logger.info("Запрос разобран: keywords=%s, sources=%s, %s..%s",
                parsed.keywords, parsed.selected_sources, parsed.date_from, parsed.date_to)

    search_id = await repository.create_search(
        query=user_query, date_from=parsed.date_from, date_to=parsed.date_to
    )

    # Уровень 1 (точные слова/словоформы) + Уровень 1.5 (семантическая близость, RAG).
    # Семантический поиск ловит смысловые совпадения, которые пропустит keyword-поиск
    # (перефразировки, синонимы, которые пользователь не указал явно).
    lexical_candidates = await preliminary_search(parsed)
    semantic_candidates = await semantic_search(parsed)
    candidates = _merge_candidates(lexical_candidates, semantic_candidates)

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
    # Уровень 2: AI-верификация каждого кандидата (и лексического, и семантического).
    # Именно здесь отсеивается всё нерелевантное и защищаемся от AI-галлюцинаций
    # (analyzer.py не доверяет цитате, которой нет дословно в тексте сообщения).
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
