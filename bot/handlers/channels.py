from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import back_to_menu_kb, channels_menu_kb, main_menu_kb
from bot.states.search_states import AddChannelStates
from collector.channel_manager import (
    ChannelAccessError,
    add_channel,
    list_channels,
    remove_channel,
    toggle_channel,
)
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router(name="channels")


async def _render_channels(message: Message):
    channels = await list_channels()
    if not channels:
        await message.answer(
            "Список каналов пуст. Добавьте первый канал.",
            reply_markup=channels_menu_kb([]),
        )
        return
    lines = ["📡 Ваши каналы:\n"]
    for ch in channels:
        mark = "✓" if ch.enabled else "✗ (отключён)"
        lines.append(f"{mark} @{ch.username} — {ch.title or ''}")
    await message.answer("\n".join(lines), reply_markup=channels_menu_kb(channels))


@router.callback_query(F.data == "menu:channels")
async def cb_channels_menu(callback: CallbackQuery):
    await callback.answer()
    await _render_channels(callback.message)


@router.message(Command("channels"))
async def cmd_channels(message: Message):
    await _render_channels(message)


@router.callback_query(F.data == "channel:add")
async def cb_add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Отправьте username канала (например, @example_channel):"
    )
    await state.set_state(AddChannelStates.waiting_for_username)


@router.message(AddChannelStates.waiting_for_username)
async def handle_add_channel_input(message: Message, state: FSMContext):
    username = message.text.strip()
    await state.clear()
    try:
        source = await add_channel(username)
        await message.answer(
            f"✅ Канал @{source.username} добавлен.", reply_markup=back_to_menu_kb()
        )
    except ChannelAccessError as e:
        await message.answer(f"⚠️ {e}", reply_markup=back_to_menu_kb())
    except Exception:
        logger.exception("Ошибка добавления канала")
        await message.answer(
            "❌ Не удалось добавить канал. Проверьте username и попробуйте снова.",
            reply_markup=back_to_menu_kb(),
        )


@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Использование: /add_channel @username")
        return
    try:
        source = await add_channel(command.args)
        await message.answer(f"✅ Канал @{source.username} добавлен.")
    except ChannelAccessError as e:
        await message.answer(f"⚠️ {e}")


@router.message(Command("remove_channel"))
async def cmd_remove_channel(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Использование: /remove_channel @username")
        return
    removed = await remove_channel(command.args)
    await message.answer("✅ Канал удалён." if removed else "Канал не найден.")


@router.callback_query(F.data.startswith("channel:toggle:"))
async def cb_toggle_channel(callback: CallbackQuery):
    username = callback.data.split(":", 2)[2]
    channels = await list_channels()
    current = next((c for c in channels if c.username == username), None)
    if current:
        await toggle_channel(username, not current.enabled)
    await callback.answer("Статус изменён")
    await _render_channels(callback.message)


@router.callback_query(F.data.startswith("channel:remove:"))
async def cb_remove_channel(callback: CallbackQuery):
    username = callback.data.split(":", 2)[2]
    await remove_channel(username)
    await callback.answer("Канал удалён")
    await _render_channels(callback.message)
