"""
Уровень 1 поиска (п.7 ТЗ): точные слова, фразы, словоформы, регистр-независимость.
Расширение запроса словоформами делается через pymorphy3, но НЕ агрессивно:
мы добавляем только нормальную форму (лемму) каждого слова как дополнительный
вариант — без синонимов и смысловых догадок. Синонимы/варианты названий
(типа "НПЗ" -> "нефтеперерабатывающий завод") пользователь либо задаёт сам
в запросе, либо это делает AI на уровне 2 (semantic), а не уровень 1.
"""
import pymorphy3

from ai.provider import AIProvider
from ai.schemas import ParsedQuery
from database import repository
from database.models import Message
from utils.logger import get_logger

logger = get_logger(__name__)
_morph = pymorphy3.MorphAnalyzer()


def expand_with_wordforms(keywords: list[str]) -> list[str]:
    """Для каждого ключевого слова/фразы добавляет леммы отдельных слов.
    Не расширяет синонимами — только грамматические формы того же слова."""
    expanded = set()
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        expanded.add(kw)
        for word in kw.split():
            parsed = _morph.parse(word)
            if parsed:
                lemma = parsed[0].normal_form
                if lemma and lemma != word.lower():
                    expanded.add(lemma)
    return list(expanded)


async def preliminary_search(parsed_query: ParsedQuery) -> list[Message]:
    """Локальный текстовый поиск-фильтр перед передачей AI (п.11 ТЗ: экономия ресурсов)."""
    keywords = expand_with_wordforms(parsed_query.keywords)

    source_ids = None
    if parsed_query.selected_sources:
        source_ids = []
        for username in parsed_query.selected_sources:
            src = await repository.get_source_by_username(username)
            if src:
                source_ids.append(src.id)

    messages = await repository.search_messages_by_keywords(
        keywords=keywords,
        source_ids=source_ids,
        date_from=parsed_query.date_from,
        date_to=parsed_query.date_to,
    )
    logger.info(
        "Предварительный поиск: %d сообщений найдено по ключевым словам %s",
        len(messages), keywords,
    )
    return messages
