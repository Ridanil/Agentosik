"""
Уровень 1.5 поиска: семантический (векторный) поиск — retrieval-часть RAG
(п.6, п.22 ТЗ).

Дополняет лексический поиск (search_engine.py): находит сообщения, близкие
по СМЫСЛУ к запросу, даже если в них нет ни одного точного ключевого слова
(например, запрос "рост цен на топливо" найдёт сообщение про "подорожание
бензина", хотя слова разные).

Важно: это только retrieval. Кандидаты отсюда всё равно проходят через
AI-анализатор (analyzer.py), который отбрасывает нерелевантное и защищает
от галлюцинаций (не доверяет цитате, которой нет дословно в тексте). То есть
семантический поиск расширяет пул кандидатов, а не заменяет верификацию.
"""
import numpy as np

from agent.embeddings import blob_to_vector, embed_text
from ai.schemas import ParsedQuery
from database import repository
from database.models import Message
from utils.logger import get_logger

logger = get_logger(__name__)


def _cosine_top_k(query_vec: np.ndarray, ids: list[int], vectors: np.ndarray, k: int) -> list[int]:
    if vectors.shape[0] == 0:
        return []
    # эмбеддинги уже нормализованы при создании -> скалярное произведение = косинусная близость
    scores = vectors @ query_vec
    top_idx = np.argsort(-scores)[:k]
    return [ids[i] for i in top_idx]


async def semantic_search(parsed_query: ParsedQuery, top_k: int = 100) -> list[Message]:
    """Возвращает top_k сообщений, семантически ближайших к смыслу запроса,
    в пределах тех же фильтров (источники/даты), что и лексический поиск."""
    query_text = parsed_query.semantic_criteria or " ".join(parsed_query.keywords)
    if not query_text.strip():
        return []

    source_ids = None
    if parsed_query.selected_sources:
        source_ids = []
        for username in parsed_query.selected_sources:
            src = await repository.get_source_by_username(username)
            if src:
                source_ids.append(src.id)

    rows = await repository.get_embeddings_for_search(
        source_ids=source_ids, date_from=parsed_query.date_from, date_to=parsed_query.date_to
    )
    if not rows:
        return []

    ids = [r[0] for r in rows]
    vectors = np.stack([blob_to_vector(r[1]) for r in rows])

    query_vec = await embed_text(query_text)

    top_ids = _cosine_top_k(query_vec, ids, vectors, top_k)
    messages = await repository.get_messages_by_ids(top_ids)
    logger.info("Семантический поиск: %d сообщений найдено по смыслу запроса", len(messages))
    return messages
