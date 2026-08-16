from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import main_menu_kb

router = Router(name="common")

WELCOME_TEXT = (
    "👋 Привет! Я локальный агент для анализа Telegram-каналов.\n\n"
    "Я умею:\n"
    "• собирать сообщения из выбранных каналов;\n"
    "• искать по ним обычным русским языком;\n"
    "• извлекать точные формулировки с ссылкой на источник;\n"
    "• ничего не придумывать от себя.\n\n"
    "Выберите действие в меню ниже."
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()


@router.message(Command("rules"))
async def cmd_rules(message: Message):
    text = (
        "📋 Правила поиска и анализа:\n\n"
        "1. Агент никогда не придумывает информацию — только текст из реальных сообщений.\n"
        "2. Если точной формулировки нет, так и указывается.\n"
        "3. Каждый результат содержит ссылку на оригинальное сообщение.\n"
        "4. Агент работает только с каналами, к которым у вас уже есть доступ.\n"
        "5. Расширение поиска по словоформам делается без добавления смысловых синонимов "
        "от себя — синонимы вы указываете в запросе сами."
    )
    await message.answer(text)
