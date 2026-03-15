from aiogram import Router, F, types
from aiogram.filters import Command
from database import (
    get_or_create_user,
    get_user_sources, add_user_source, toggle_source, delete_source,
    get_user_drafts, get_draft, update_draft_text, update_draft_status, delete_draft,
    get_user_stats, initialize_default_sources, schedule_post
)
from inline_menu import (
    get_main_menu_keyboard,
    get_sources_keyboard,
    get_draft_keyboard,
    get_draft_keyboard,
    get_settings_keyboard,
    get_back_keyboard,
    get_schedule_keyboard
)
from keyboards import get_main_reply_keyboard
from config import DB_NAME
from datetime import datetime, timedelta
import aiosqlite

router = Router()
edit_states = {}

# ===========================
# 🎯 Main Menu
# ===========================

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Главное меню с Reply-клавиатурой"""
    
    user = await get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    # Всегда показываем Reply-клавиатуру
    await message.answer(
        "🤖 **AI Content Bot**\n\n"
        "Автоматическая генерация постов для Telegram-каналов про ИИ.\n\n"
        "Выбери раздел из меню внизу 👇",
        reply_markup=get_main_reply_keyboard()
    )
    
    # Добавляем источники по умолчанию для новых
    if user and not await get_user_sources(message.from_user.id):
        await initialize_default_sources(message.from_user.id)

# ===========================
# 📊 Statistics
# ===========================

@router.message(F.text == "📊 Статистика")
async def handle_stats(message: types.Message):
    """Показать статистику"""
    
    stats = await get_user_stats(message.from_user.id)
    
    text = f"""
📊 **Статистика**

📰 Источников активно: {stats['active_sources']}

📝 Черновики:
• В ожидании: {stats['pending']}
• Опубликованы: {stats['published']}
• Пропущены: {stats['skipped']}

📈 Всего создано: {stats['total_drafts']}
"""
    
    await message.answer(text)

# ===========================
# 📰 Sources
# ===========================

@router.message(F.text == "📰 Источники")
async def handle_sources(message: types.Message):
    """Список источников"""
    
    sources = await get_user_sources(message.from_user.id)
    
    if not sources:
        text = "📰 У тебя пока нет источников"
    else:
        text = "📰 **Твои источники**\n\n"
        for i, source in enumerate(sources, 1):
            status = "✅" if source['enabled'] else "❌"
            text += f"{status} {i}. **{source['name']}**\n"
            text += f"   {source['rss_url'][:50]}...\n\n"
    
    await message.answer(
        text,
        reply_markup=get_sources_keyboard(sources) if sources else None
    )

# ===========================
# 📝 Drafts
# ===========================

@router.message(F.text == "✏️ Черновики")
async def handle_drafts(message: types.Message):
    """Список черновиков с кнопками управления"""
    from inline_menu import get_draft_keyboard
    
    drafts = await get_user_drafts(message.from_user.id, limit=5)
    
    if not drafts:
        await message.answer("📭 У тебя пока нет активных черновиков.")
        return
    
    await message.answer(f"📝 **Последние черновики ({len(drafts)} шт.):**")
    
    for draft in drafts:
        status_emoji = {"pending": "⏳", "published": "✅", "skipped": "❌", "scheduled": "⏰"}
        status = status_emoji.get(draft['status'], '📄')
        
        text = f"""
{status} **{draft['title']}**
━━━━━━━━━━━━━━━━
{draft['post_text']}

━━━━━━━━━━━━━━━━
🔗 Источник: {draft['source_name']}
🆔 ID: {draft['id']}
"""
        await message.answer(
            text=text.strip(),
            reply_markup=get_draft_keyboard(draft['id']),
            parse_mode='Markdown'
        )

# ===========================
# ⚙️ Settings
# ===========================

@router.message(F.text == "⚙️ Настройки")
async def handle_settings(message: types.Message):
    """Настройки"""
    
    await message.answer(
        "⚙️ **Настройки**\n\nВыбери действие:",
        reply_markup=get_settings_keyboard()
    )

# ===========================
# ❓ Help
# ===========================

@router.message(F.text == "❓ Помощь")
async def handle_help(message: types.Message):
    """Помощь"""
    
    text = """
❓ **Помощь**

📖 **Как использовать:**
1. Добавь RSS-источники в разделе «Источники»
2. Бот автоматически найдёт новости
3. Генерирует посты с помощью ИИ
4. Ты получаешь черновики с кнопками
5. Опубликуй, отредактируй или пропусти

⌨️ **Команды:**
/start - Главное меню
/stats - Статистика
/drafts - Черновики
/help - Помощь
/cancel - Отмена действия

💡 **Советы:**
• Добавляй только релевантные источники
• Проверяй черновики перед публикацией
• Используй разные стили постов

📧 **Поддержка:**
@your_support_username
"""
    
    await message.answer(text)

# ===========================
# 🔘 Inline Callbacks
# ===========================

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "🤖 **AI Content Bot**\n\nВыбери раздел:",
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "stats")
async def cb_stats(callback: types.CallbackQuery):
    """Статистика (inline)"""
    
    stats = await get_user_stats(callback.from_user.id)
    
    text = f"""
📊 **Статистика**

📰 Источников активно: {stats['active_sources']}

📝 Черновики:
• В ожидании: {stats['pending']}
• Опубликованы: {stats['published']}
• Пропущены: {stats['skipped']}

📈 Всего создано: {stats['total_drafts']}
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "sources")
async def cb_sources(callback: types.CallbackQuery):
    """Источники (inline)"""
    
    sources = await get_user_sources(callback.from_user.id)
    
    if not sources:
        text = "📰 У тебя пока нет источников"
    else:
        text = "📰 **Твои источники**\n\n"
        for i, source in enumerate(sources, 1):
            status = "✅" if source['enabled'] else "❌"
            text += f"{status} {i}. {source['name']}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_sources_keyboard(sources)
    )

@router.callback_query(F.data.startswith("toggle_source_"))
async def cb_toggle_source(callback: types.CallbackQuery):
    """Включить/выключить источник"""
    
    source_id = int(callback.data.split("_")[-1])
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT enabled FROM user_sources WHERE id = ? AND user_id = ?",
            (source_id, callback.from_user.id)
        )
        row = await cursor.fetchone()
        
        if row:
            new_status = not row[0]
            await toggle_source(callback.from_user.id, source_id, new_status)
    
    await cb_sources(callback)

@router.callback_query(F.data == "add_source")
async def cb_add_source(callback: types.CallbackQuery):
    """Добавить источник"""
    await callback.message.answer(
        "📝 **Добавление источника**\n\n"
        "Отправь данные в формате:\n"
        "```\n"
        "Название: Мой источник\n"
        "URL: https://example.com/rss\n"
        "Ключевые слова: ai, нейросеть, gpt\n"
        "```\n\n"
        "Или отправь /cancel для отмены"
    )
    edit_states[callback.from_user.id] = 'add_source'

@router.callback_query(F.data == "drafts")
async def cb_drafts(callback: types.CallbackQuery):
    """Черновики (inline)"""
    
    drafts = await get_user_drafts(callback.from_user.id, limit=5)
    
    if not drafts:
        text = "📭 Нет активных черновиков"
    else:
        text = "📝 **Последние черновики**\n\n"
        for draft in drafts:
            status_emoji = {"pending": "⏳", "published": "✅", "skipped": "❌", "scheduled": "⏰"}
            text += f"{status_emoji.get(draft['status'])} {draft['title'][:50]}...\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data.startswith("approve_"))
async def cb_approve_draft(callback: types.CallbackQuery):
    """Опубликовать черновик сейчас"""
    from database import get_user_channel

    draft_id = int(callback.data.split("_")[-1])
    draft = await get_draft(draft_id)
    channel_id = await get_user_channel(callback.from_user.id)

    if not draft:
        await callback.answer("❌ Черновик не найден", show_alert=True)
        return

    if not channel_id:
        await callback.answer("📢 Сначала привяжите канал в Настройках!", show_alert=True)
        return

    try:
        await callback.bot.send_message(
            chat_id=channel_id,
            text=draft['post_text'],
            parse_mode='Markdown'
        )
        await update_draft_status(draft_id, 'published')
        await callback.answer("✅ Опубликовано в канал!", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        await callback.answer(f"❌ Ошибка публикации: {e}", show_alert=True)

@router.callback_query(F.data.startswith("pre_schedule_"))
async def cb_pre_schedule(callback: types.CallbackQuery):
    """Запросить время планирования"""
    draft_id = int(callback.data.split("_")[-1])
    from inline_menu import get_schedule_keyboard
    await callback.message.edit_reply_markup(reply_markup=get_schedule_keyboard(draft_id))

@router.callback_query(F.data.startswith("do_schedule_"))
async def cb_do_schedule(callback: types.CallbackQuery):
    """Запланировать на выбранное время"""
    from database import schedule_post, get_user_channel
    from datetime import datetime, timedelta

    parts = callback.data.split("_")
    draft_id = int(parts[2])
    hours = int(parts[3])

    channel_id = await get_user_channel(callback.from_user.id)
    if not channel_id:
        await callback.answer("📢 Сначала привяжите канал в Настройках!", show_alert=True)
        return

    scheduled_time = datetime.now() + timedelta(hours=hours)
    await schedule_post(callback.from_user.id, draft_id, scheduled_time)

    await callback.answer(f"📅 Запланировано на {scheduled_time.strftime('%H:%M %d.%m')}", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)

@router.callback_query(F.data == "set_channel")
async def cb_set_channel(callback: types.CallbackQuery):
    """Запрос ID канала"""
    await callback.message.answer(
        "📢 **Привязка канала**\n\n"
        "1. Добавь бота в администраторы своего канала\n"
        "2. Отправь мне ID канала (например, `@my_channel` или `-100...`)\n\n"
        "Или отправь /cancel для отмены"
    )
    edit_states[callback.from_user.id] = 'set_channel'


@router.callback_query(F.data.startswith("edit_"))
async def cb_edit_draft(callback: types.CallbackQuery):
    """Редактировать черновик"""
    
    draft_id = int(callback.data.split("_")[-1])
    edit_states[callback.from_user.id] = f'edit_{draft_id}'
    
    await callback.message.answer(
        "✏️ Отправь новый текст черновика:\n\n"
        "Или /cancel для отмены"
    )

@router.callback_query(F.data.startswith("skip_"))
async def cb_skip_draft(callback: types.CallbackQuery):
    """Пропустить черновик"""
    
    draft_id = int(callback.data.split("_")[-1])
    await update_draft_status(draft_id, 'skipped')
    
    await callback.answer("❌ Пропущено", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)

@router.callback_query(F.data == "settings")
async def cb_settings(callback: types.CallbackQuery):
    """Настройки (inline)"""
    
    await callback.message.edit_text(
        "⚙️ **Настройки**\n\nВыбери действие:",
        reply_markup=get_settings_keyboard()
    )

@router.callback_query(F.data == "reset_sources")
async def cb_reset_sources(callback: types.CallbackQuery):
    """Сбросить источники"""
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM user_sources WHERE user_id = ?",
            (callback.from_user.id,)
        )
        await db.commit()
    
    await initialize_default_sources(callback.from_user.id)
    
    await callback.message.answer("✅ Источники сброшены к стандартным")
    await cb_settings(callback)

@router.callback_query(F.data == "help")
async def cb_help(callback: types.CallbackQuery):
    """Помощь (inline)"""
    
    text = """
❓ **Помощь**

📖 **Как использовать:**
1. Добавь RSS-источники
2. Бот найдёт новости
3. Генерирует посты с ИИ
4. Ты получаешь черновики
5. Опубликуй или отредактируй

⌨️ **Команды:**
/start - Главное меню
/stats - Статистика
/drafts - Черновики
/help - Помощь

📧 **Поддержка:**
@your_support_username
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard()
    )

# ===========================
# ⏰ ФУНКЦИИ ПЛАНИРОВАНИЯ (НОВЫЕ!)
# ===========================

@router.callback_query(F.data.startswith("schedule_menu_"))
async def cb_schedule_menu(callback: types.CallbackQuery):
    """Показать меню планирования"""
    
    draft_id = int(callback.data.split("_")[-1])
    
    await callback.message.answer(
        "⏰ **Выбери время публикации:**",
        reply_markup=get_schedule_keyboard(draft_id)
    )

@router.callback_query(F.data.startswith("schedule_"))
async def cb_schedule_post(callback: types.CallbackQuery):
    """Запланировать пост"""
    
    parts = callback.data.split("_")
    draft_id = int(parts[1])
    time_option = parts[2]
    
    # Вычисляем время
    now = datetime.now()
    
    if time_option.isdigit():
        hours = int(time_option)
        scheduled_time = now + timedelta(hours=hours)
        time_str = scheduled_time.strftime("%d.%m.%Y %H:%M")
    elif time_option == "tomorrow_morning":
        tomorrow = now + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=9, minute=0, second=0)
        time_str = scheduled_time.strftime("%d.%m.%Y 09:00")
    elif time_option == "tomorrow_evening":
        tomorrow = now + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=18, minute=0, second=0)
        time_str = scheduled_time.strftime("%d.%m.%Y 18:00")
    else:
        await callback.answer("❌ Неверный формат времени", show_alert=True)
        return
    
    # Сохраняем в БД
    await schedule_post(
        user_id=callback.from_user.id,
        draft_id=draft_id,
        scheduled_time=scheduled_time.isoformat()
    )
    
    # Меняем статус черновика
    await update_draft_status(draft_id, 'scheduled')
    
    await callback.message.answer(
        f"✅ **Пост запланирован!**\n\n"
        f"📅 Время: {time_str}\n\n"
        f"Бот автоматически опубликует пост в указанное время."
    )
    
    await callback.message.edit_reply_markup(reply_markup=None)

@router.callback_query(F.data.startswith("cancel_schedule_"))
async def cb_cancel_schedule(callback: types.CallbackQuery):
    """Отмена планирования"""
    
    draft_id = int(callback.data.split("_")[-1])
    
    await callback.message.answer(
        "❌ Планирование отменено",
        reply_markup=get_draft_keyboard(draft_id)
    )

# ===========================
# 📝 Text Handler
# ===========================

@router.message(F.text)
async def handle_text_input(message: types.Message):
    """Обработка текстовых сообщений"""
    
    user_id = message.from_user.id
    
    if user_id not in edit_states:
        return
    
    state = edit_states[user_id]
    
    if state == 'add_source':
        try:
            lines = message.text.strip().split('\n')
            data = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    data[key.strip().lower()] = value.strip()
            
            name = data.get('название', data.get('name', ''))
            url = data.get('url', '')
            keywords = data.get('ключевые слова', data.get('keywords', ''))
            
            if not name or not url:
                await message.answer("❌ Укажи название и URL")
                return
            
            await add_user_source(user_id, name, url, keywords)
            await message.answer(
                f"✅ Источник «{name}» добавлен!",
                reply_markup=get_main_reply_keyboard()
            )
            
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")
        
        finally:
            del edit_states[user_id]
    
    elif state.startswith('edit_'):
        draft_id = int(state.split('_')[-1])
        new_text = message.text
        
        await update_draft_text(draft_id, new_text)
        
        await message.answer(
            "✅ Текст обновлён!",
            reply_markup=get_draft_keyboard(draft_id)
        )
        
        del edit_states[user_id]

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    """Отмена действия"""
    
    user_id = message.from_user.id
    
    if user_id in edit_states:
        del edit_states[user_id]
        await message.answer(
            "✖️ Отменено",
            reply_markup=get_main_reply_keyboard()
        )
    else:
        await message.answer("📭 Нет активного действия")

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Статистика командой"""
    await handle_stats(message)

@router.message(Command("drafts"))
async def cmd_drafts(message: types.Message):
    """Черновики командой"""
    await handle_drafts(message)