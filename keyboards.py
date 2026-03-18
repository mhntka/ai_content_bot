from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура (всегда видна внизу)"""
    
    keyboard = [
        [
            KeyboardButton(text="📂 Выбрать канал")
        ],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="📰 Источники")
        ],
        [
            KeyboardButton(text="✏️ Черновики"),
            KeyboardButton(text="⚙️ Настройки")
        ],
        [
            KeyboardButton(text="❓ Помощь")
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    
    keyboard = [
        [KeyboardButton(text="❌ Отмена")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )