from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from agent.core import run_search
from ai.factory import get_ai_provider
from bot.keyboards.main_menu import back_to_menu_kb
from bot.states.search_states import SearchStates
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router(name="search")


def format_results(results: list[dict]) -> str:
    if not results:
        return "По вашему запросу релевантных сообщений не найдено."

    lines = [f"🔎 Найдено {len(results)} релевантных сообщения(й)\n"]
    relevance_labels = {"high": "Высокая", "medium": "Средняя", "low": "Низкая"}
    for r in results:
        lines.append(f"Источник: {r['channel_username']}")
        lines.append(f"Дата: {r['message_date'] or 'неизвестна'}")
        lines.append(f"\nФормулировка:\n«{r['quote']}»\n")
        lines.append(f"Почему подходит:\n{r['explanation']}\n")
        lines.append(f"Источник: {r['message_url']}")
        lines.append(f"Релевантность: {relevance_labels.get(r['confidence'], r['confidence'])}")
        lines.append("―" * 20)
    return "\n".join(lines)


@router.callback_query(F.data == "menu:search")
async def cb_search_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Напишите, что нужно найти, обычным русским языком.\n\n"
        "Пример: «Найди за последние 7 дней сообщения о пожаре или повреждении "
        "НПЗ, вытащи точную формулировку и дай ссылку на оригинал.»"
    )
    await state.set_state(SearchStates.waiting_for_query)


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await message.answer("Напишите поисковый запрос обычным русским языком:")
    await state.set_state(SearchStates.waiting_for_query)


@router.message(SearchStates.waiting_for_query)
async def handle_search_query(message: Message, state: FSMContext):
    await state.clear()
    query = message.text.strip()
    status_msg = await message.answer("🔄 Анализирую запрос и ищу сообщения, подождите...")

    try:
        ai = get_ai_provider()
        outcome = await run_search(ai, query)
    except Exception:
        logger.exception("Ошибка выполнения поиска")
        await status_msg.edit_text(
            "❌ Произошла ошибка при поиске. Проверьте, что Ollama запущен, и попробуйте снова.",
            reply_markup=back_to_menu_kb(),
        )
        return

    if outcome["candidates_count"] == 0:
        await status_msg.edit_text(
            "По вашему запросу не найдено ни одного кандидата в локальной базе.\n"
            "Возможно, стоит переформулировать запрос или собрать больше сообщений.",
            reply_markup=back_to_menu_kb(),
        )
        return

    text = format_results(outcome["results"])
    # Telegram ограничивает длину сообщения — режем на части при необходимости
    for chunk_start in range(0, len(text), 3500):
        await message.answer(text[chunk_start:chunk_start + 3500])
    await message.answer("Готово ✅", reply_markup=back_to_menu_kb())
