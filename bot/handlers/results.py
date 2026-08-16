from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import back_to_menu_kb
from collector.channel_manager import list_channels
from config.settings import settings
from database import repository

router = Router(name="results")


def _format_latest(rows: list[dict]) -> str:
    if not rows:
        return "Результатов пока нет. Выполните поиск через 🔎 Новый поиск."
    lines = ["📥 Последние результаты:\n"]
    for r in rows:
        lines.append(f"Запрос: {r['search_query']}")
        lines.append(f"Источник: @{r['source_username']}")
        lines.append(f"Дата: {r['message_date'] or 'неизвестна'}")
        lines.append(f"Формулировка: «{r['quote']}»")
        lines.append(f"Ссылка: {r['message_url']}")
        lines.append("―" * 20)
    return "\n".join(lines)


@router.callback_query(F.data == "menu:results")
async def cb_results(callback: CallbackQuery):
    await callback.answer()
    rows = await repository.get_latest_results(limit=10)
    await callback.message.answer(_format_latest(rows), reply_markup=back_to_menu_kb())


@router.message(Command("results"))
async def cmd_results(message: Message):
    rows = await repository.get_latest_results(limit=10)
    await message.answer(_format_latest(rows))


@router.callback_query(F.data == "menu:status")
async def cb_status(callback: CallbackQuery):
    await callback.answer()
    channels = await list_channels()
    enabled = [c for c in channels if c.enabled]
    text = (
        "📊 Статус системы:\n\n"
        f"Каналов всего: {len(channels)}\n"
        f"Активных каналов: {len(enabled)}\n"
        f"AI-модель: {settings.ollama_model}\n"
        f"Ollama: {settings.ollama_host}\n"
    )
    await callback.message.answer(text, reply_markup=back_to_menu_kb())


@router.message(Command("status"))
async def cmd_status(message: Message):
    channels = await list_channels()
    enabled = [c for c in channels if c.enabled]
    text = (
        "📊 Статус системы:\n\n"
        f"Каналов всего: {len(channels)}\n"
        f"Активных каналов: {len(enabled)}\n"
        f"AI-модель: {settings.ollama_model}\n"
        f"Ollama: {settings.ollama_host}\n"
    )
    await message.answer(text)


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery):
    await callback.answer()
    text = (
        "⚙️ Настройки (редактируются в файле .env):\n\n"
        f"Модель: {settings.ollama_model}\n"
        f"Макс. сообщений в батче AI: {settings.max_messages_per_ai_batch}\n"
    )
    await callback.message.answer(text, reply_markup=back_to_menu_kb())
