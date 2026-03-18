from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.enums import ParseMode

from database import (
    get_or_create_user, get_user,
    get_user_channels, get_channel, add_channel, delete_channel, set_active_channel,
    get_channel_sources, add_channel_source, toggle_source, initialize_default_sources,
    get_channel_drafts, get_draft, update_draft_text, update_draft_status, schedule_post,
    get_channel_stats
)
from inline_menu import (
    get_main_menu_keyboard,
    get_sources_keyboard,
    get_draft_keyboard,
    get_settings_keyboard,
    get_back_keyboard,
    get_schedule_keyboard,
    get_channels_keyboard
)
from keyboards import get_main_reply_keyboard
from datetime import datetime, timedelta

router = Router()
edit_states = {}

# Вспомогательная функция проверки канала
async def get_active_channel_or_notify(user_id: int, message_or_callback) -> int | None:
    user = await get_user(user_id)
    if not user or not user.active_channel_id:
        text = "⚠️ Сначала выберите или добавьте канал в меню <b>«📂 Выбрать канал»</b>."
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(text, parse_mode=ParseMode.HTML)
        else:
            await message_or_callback.answer(text, show_alert=True)
        return None
    return user.active_channel_id

# ===========================
# 🎯 Main Menu
# ===========================

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    await message.answer(
        "🤖 <b>AI Content Bot</b>\n\n"
        "Автоматическая генерация постов для Telegram-каналов.\n\n"
        "Выбери раздел из меню внизу 👇",
        reply_markup=get_main_reply_keyboard(),
        parse_mode=ParseMode.HTML
    )

# ===========================
# 📂 Channels
# ===========================

@router.message(F.text == "📂 Выбрать канал")
async def handle_channels(message: types.Message):
    user = await get_user(message.from_user.id)
    channels = await get_user_channels(message.from_user.id)
    
    await message.answer(
        "📂 <b>Управление каналами</b>\n\nВыберите канал для работы:",
        reply_markup=get_channels_keyboard(channels, user.active_channel_id if user else None),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "select_channel")
async def cb_select_channel(callback: types.CallbackQuery):
    user = await get_user(callback.from_user.id)
    channels = await get_user_channels(callback.from_user.id)
    
    await callback.message.edit_text(
        "📂 <b>Управление каналами</b>\n\nВыберите канал для работы:",
        reply_markup=get_channels_keyboard(channels, user.active_channel_id if user else None),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("set_channel_"))
async def cb_set_channel(callback: types.CallbackQuery):
    channel_id = int(callback.data.split("_")[-1])
    await set_active_channel(callback.from_user.id, channel_id)
    
    channel = await get_channel(channel_id)
    await callback.answer(f"✅ Выбран канал: {channel.name}")
    await cb_select_channel(callback)

@router.callback_query(F.data == "add_channel")
async def cb_add_channel(callback: types.CallbackQuery):
    channels = await get_user_channels(callback.from_user.id)
    if len(channels) >= 5:
        await callback.answer("❌ Достигнут лимит (5 каналов).", show_alert=True)
        return
        
    await callback.message.answer(
        "📝 <b>Добавление канала</b>\n\n"
        "1. Добавь бота в администраторы своего канала.\n"
        "2. Отправь мне данные в формате:\n\n"
        "<code>\n"
        "Имя: Мой Канал\n"
        "ID: @my_channel\n"
        "</code>\n\n"
        "Или отправь /cancel для отмены",
        parse_mode=ParseMode.HTML
    )
    edit_states[callback.from_user.id] = 'add_channel'

@router.callback_query(F.data == "delete_channel")
async def cb_delete_channel(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id: return
    
    await delete_channel(channel_id)
    await callback.answer("🗑 Канал удален", show_alert=True)
    await cb_select_channel(callback)

# ===========================
# 📊 Statistics
# ===========================

@router.message(F.text == "📊 Статистика")
async def handle_stats(message: types.Message):
    channel_id = await get_active_channel_or_notify(message.from_user.id, message)
    if not channel_id: return
    
    stats = await get_channel_stats(channel_id)
    channel = await get_channel(channel_id)
    
    text = f"""
📊 <b>Статистика для {channel.name}</b>

📰 Источников активно: {stats['active_sources']}

📝 Черновики:
• В ожидании: {stats['pending']}
• Опубликованы: {stats['published']}
• Пропущены: {stats['skipped']}

📈 Всего создано: {stats['total_drafts']}
"""
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "stats")
async def cb_stats(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id: return
    
    stats = await get_channel_stats(channel_id)
    channel = await get_channel(channel_id)
    
    text = f"""
📊 <b>Статистика для {channel.name}</b>

📰 Источников активно: {stats['active_sources']}

📝 Черновики:
• В ожидании: {stats['pending']}
• Опубликованы: {stats['published']}
• Пропущены: {stats['skipped']}

📈 Всего создано: {stats['total_drafts']}
"""
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)

# ===========================
# 📰 Sources
# ===========================

@router.message(F.text == "📰 Источники")
async def handle_sources(message: types.Message):
    channel_id = await get_active_channel_or_notify(message.from_user.id, message)
    if not channel_id: return
    
    sources = await get_channel_sources(channel_id)
    channel = await get_channel(channel_id)
    
    if not sources:
        text = f"📰 В канале <b>{channel.name}</b> пока нет источников."
    else:
        text = f"📰 <b>Источники ({channel.name})</b>\n\n"
        for i, source in enumerate(sources, 1):
            status = "✅" if source.enabled else "❌"
            text += f"{status} {i}. <b>{source.name}</b>\n"
            text += f"   {source.rss_url[:50]}...\n\n"
    
    await message.answer(text, reply_markup=get_sources_keyboard(sources) if sources else None, parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "sources")
async def cb_sources(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id: return
    
    sources = await get_channel_sources(channel_id)
    channel = await get_channel(channel_id)
    
    if not sources:
        text = f"📰 В канале <b>{channel.name}</b> пока нет источников."
    else:
        text = f"📰 <b>Источники ({channel.name})</b>\n\n"
        for i, source in enumerate(sources, 1):
            status = "✅" if source.enabled else "❌"
            text += f"{status} {i}. {source.name}\n"
    
    await callback.message.edit_text(text, reply_markup=get_sources_keyboard(sources), parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("toggle_source_"))
async def cb_toggle_source(callback: types.CallbackQuery):
    source_id = int(callback.data.split("_")[-1])
    
    # We should technically check if this source belongs to active channel, but simplified here.
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id: return
    
    sources = await get_channel_sources(channel_id)
    source = next((s for s in sources if s.id == source_id), None)
    if source:
        await toggle_source(source_id, not source.enabled)
    
    await cb_sources(callback)

@router.callback_query(F.data == "add_source")
async def cb_add_source(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id: return
    
    await callback.message.answer(
        "📝 <b>Добавление источника</b>\n\n"
        "Отправь данные в формате:\n"
        "<code>\n"
        "Название: Мой источник\n"
        "URL: https://example.com/rss\n"
        "Ключевые слова: ai, нейросеть, gpt\n"
        "</code>\n\n"
        "Или отправь /cancel для отмены",
        parse_mode=ParseMode.HTML
    )
    edit_states[callback.from_user.id] = 'add_source'

# ===========================
# 📝 Drafts
# ===========================

@router.message(F.text == "✏️ Черновики")
async def handle_drafts(message: types.Message):
    channel_id = await get_active_channel_or_notify(message.from_user.id, message)
    if not channel_id: return
    
    drafts = await get_channel_drafts(channel_id, limit=5)
    
    if not drafts:
        await message.answer("📭 У тебя пока нет активных черновиков.", parse_mode=ParseMode.HTML)
        return
    
    await message.answer(f"📝 <b>Последние черновики ({len(drafts)} шт.):</b>", parse_mode=ParseMode.HTML)
    
    for draft in drafts:
        status_emoji = {"pending": "⏳", "published": "✅", "skipped": "❌", "scheduled": "⏰"}
        status = status_emoji.get(draft.status, '📄')
        
        text = f"""
{status} <b>{draft.title}</b>
━━━━━━━━━━━━━━━━
{draft.post_text}

━━━━━━━━━━━━━━━━
🔗 Источник: {draft.source_name}
🆔 ID: {draft.id}
"""
        if draft.image_url:
            text += f"\n🖼️ Картинка: Прикреплена"
            await message.answer_photo(
                photo=draft.image_url,
                caption=text.strip(),
                reply_markup=get_draft_keyboard(draft.id),
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(
                text=text.strip(),
                reply_markup=get_draft_keyboard(draft.id),
                parse_mode=ParseMode.HTML
            )

@router.callback_query(F.data == "drafts")
async def cb_drafts(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id: return
    
    drafts = await get_channel_drafts(channel_id, limit=5)
    
    if not drafts:
        text = "📭 Нет активных черновиков"
    else:
        text = "📝 <b>Последние черновики</b>\n\n"
        for draft in drafts:
            status_emoji = {"pending": "⏳", "published": "✅", "skipped": "❌", "scheduled": "⏰"}
            text += f"{status_emoji.get(draft.status)} {draft.title[:50]}...\n"
    
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("approve_"))
async def cb_approve_draft(callback: types.CallbackQuery):
    draft_id = int(callback.data.split("_")[-1])
    draft = await get_draft(draft_id)
    
    if not draft:
        await callback.answer("❌ Черновик не найден", show_alert=True)
        return

    channel = await get_channel(draft.channel_id)

    try:
        if draft.image_url:
            await callback.bot.send_photo(
                chat_id=channel.tg_channel_id,
                photo=draft.image_url,
                caption=draft.post_text,
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.bot.send_message(
                chat_id=channel.tg_channel_id,
                text=draft.post_text,
                parse_mode=ParseMode.HTML
            )
        await update_draft_status(draft_id, 'published')
        await callback.answer("✅ Опубликовано в канал!", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        await callback.answer(f"❌ Ошибка публикации: {e}", show_alert=True)

@router.callback_query(F.data.startswith("pre_schedule_"))
async def cb_pre_schedule(callback: types.CallbackQuery):
    draft_id = int(callback.data.split("_")[-1])
    await callback.message.edit_reply_markup(reply_markup=get_schedule_keyboard(draft_id))

@router.callback_query(F.data.startswith("do_schedule_"))
async def cb_do_schedule(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    draft_id = int(parts[2])
    hours = int(parts[3])

    draft = await get_draft(draft_id)
    if not draft: return
    
    scheduled_time = datetime.now() + timedelta(hours=hours)
    await schedule_post(draft.channel_id, draft_id, scheduled_time)

    await callback.answer(f"📅 Запланировано на {scheduled_time.strftime('%H:%M %d.%m')}", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)

@router.callback_query(F.data.startswith("edit_"))
async def cb_edit_draft(callback: types.CallbackQuery):
    draft_id = int(callback.data.split("_")[-1])
    edit_states[callback.from_user.id] = f'edit_{draft_id}'
    
    await callback.message.answer("✏️ Отправь новый текст черновика:\n\nИли /cancel для отмены")

@router.callback_query(F.data.startswith("skip_"))
async def cb_skip_draft(callback: types.CallbackQuery):
    draft_id = int(callback.data.split("_")[-1])
    await update_draft_status(draft_id, 'skipped')
    await callback.answer("❌ Пропущено", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)

# ===========================
# ⚙️ Settings
# ===========================

@router.message(F.text == "⚙️ Настройки")
async def handle_settings(message: types.Message):
    await message.answer("⚙️ <b>Настройки</b>\n\nВыбери действие:", reply_markup=get_settings_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "settings")
async def cb_settings(callback: types.CallbackQuery):
    await callback.message.edit_text("⚙️ <b>Настройки</b>\n\nВыбери действие:", reply_markup=get_settings_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "reset_sources")
async def cb_reset_sources(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id: return
    
    sources = await get_channel_sources(channel_id)
    for s in sources:
        from database import delete_source
        await delete_source(s.id)
        
    await initialize_default_sources(channel_id)
    await callback.answer("✅ Источники сброшены к стандартным", show_alert=True)
    await cb_settings(callback)

# ===========================
# ❓ Help
# ===========================

@router.message(F.text == "❓ Помощь")
async def handle_help(message: types.Message):
    text = """
❓ <b>Помощь</b>

📖 <b>Как использовать:</b>
1. Выбери или добавь канал в меню
2. Настрой RSS-источники
3. Бот генерирует черновики с фото
4. Опубликуй или запланируй

/start - Главное меню
/cancel - Отмена действия
"""
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🤖 <b>AI Content Bot</b>\n\nВыбери раздел:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

# ===========================
# 📝 Text Handler
# ===========================

@router.message(F.text)
async def handle_text_input(message: types.Message):
    user_id = message.from_user.id
    if user_id not in edit_states:
        return
    
    state = edit_states[user_id]
    
    if state == 'add_channel':
        try:
            lines = message.text.strip().split('\n')
            data = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    data[key.strip().lower()] = value.strip()
            
            name = data.get('имя', data.get('name', 'Без названия'))
            tg_id = data.get('id', '')
            
            if not tg_id:
                await message.answer("❌ Укажи ID канала (например, @my_channel)")
                return
                
            channel = await add_channel(user_id, tg_id, name)
            await set_active_channel(user_id, channel.id)
            await initialize_default_sources(channel.id)
            
            await message.answer(
                f"✅ Канал <b>{name}</b> добавлен и выбран активным!\nБазовые источники подключены.",
                reply_markup=get_main_reply_keyboard(),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")
        finally:
            del edit_states[user_id]
            
    elif state == 'add_source':
        channel_id = await get_active_channel_or_notify(user_id, message)
        if not channel_id:
            del edit_states[user_id]
            return
            
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
            
            await add_channel_source(channel_id, name, url, keywords)
            await message.answer(f"✅ Источник «{name}» добавлен!", reply_markup=get_main_reply_keyboard())
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")
        finally:
            del edit_states[user_id]
            
    elif state.startswith('edit_'):
        draft_id = int(state.split('_')[-1])
        await update_draft_text(draft_id, message.text)
        await message.answer("✅ Текст обновлён!", reply_markup=get_draft_keyboard(draft_id))
        del edit_states[user_id]

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    user_id = message.from_user.id
    if user_id in edit_states:
        del edit_states[user_id]
        await message.answer("✖️ Отменено", reply_markup=get_main_reply_keyboard())
    else:
        await message.answer("📭 Нет активного действия")
