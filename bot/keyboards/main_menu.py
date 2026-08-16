from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📡 Каналы", callback_data="menu:channels")],
            [InlineKeyboardButton(text="🔎 Новый поиск", callback_data="menu:search")],
            [InlineKeyboardButton(text="📥 Последние результаты", callback_data="menu:results")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings")],
            [InlineKeyboardButton(text="📊 Статус", callback_data="menu:status")],
        ]
    )


def channels_menu_kb(channels: list) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        mark = "✅" if ch.enabled else "⛔️"
        rows.append([
            InlineKeyboardButton(
                text=f"{mark} @{ch.username}",
                callback_data=f"channel:toggle:{ch.username}",
            ),
            InlineKeyboardButton(text="🗑", callback_data=f"channel:remove:{ch.username}"),
        ])
    rows.append([InlineKeyboardButton(text="➕ Добавить канал", callback_data="channel:add")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")]]
    )
