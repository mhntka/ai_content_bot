from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import SUBSCRIPTION_PRICES

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="📰 Источники", callback_data="sources")
        ],
        [
            InlineKeyboardButton(text="✏️ Черновики", callback_data="drafts"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
        ],
        [
            InlineKeyboardButton(text="💳 Подписка", callback_data="subscribe")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ])

def get_sources_keyboard(sources: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком источников"""
    keyboard = []
    
    for source in sources:
        status = "✅" if source['enabled'] else "❌"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {source['name']}",
                callback_data=f"toggle_source_{source['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить источник", callback_data="add_source")
    ])
    
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_draft_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    """Кнопки для черновика"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сейчас", callback_data=f"approve_{draft_id}"),
            InlineKeyboardButton(text="📅 Запланировать", callback_data=f"pre_schedule_{draft_id}")
        ],
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{draft_id}"),
            InlineKeyboardButton(text="❌ Пропустить", callback_data=f"skip_{draft_id}")
        ]
    ])

def get_schedule_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени отложенного поста"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="+1 час", callback_data=f"do_schedule_{draft_id}_1"),
            InlineKeyboardButton(text="+3 часа", callback_data=f"do_schedule_{draft_id}_3")
        ],
        [
            InlineKeyboardButton(text="+6 часов", callback_data=f"do_schedule_{draft_id}_6"),
            InlineKeyboardButton(text="+12 часов", callback_data=f"do_schedule_{draft_id}_12")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с тарифами"""
    keyboard = []
    
    for tariff_key, tariff_info in SUBSCRIPTION_PRICES.items():
        keyboard.append([
            InlineKeyboardButton(
                text=f"⭐ {tariff_info['name']} ({tariff_info['stars']} Stars)",
                callback_data=f"pay_{tariff_key}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Привязать канал", callback_data="set_channel")
        ],
        [
            InlineKeyboardButton(text="🔄 Сбросить источники", callback_data="reset_sources")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        ]
    ])

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Просто кнопка назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])