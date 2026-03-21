from aiogram import Router, F, types
from aiogram.types import ChatMemberUpdated
from aiogram.filters import (
    Command,
    ChatMemberUpdatedFilter,
    IS_NOT_MEMBER,
    ADMINISTRATOR,
)
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext

from states import ChannelStates, SourceStates, DraftStates
from database import (
    get_or_create_user,
    get_user,
    get_user_channels,
    get_channel,
    delete_channel,
    set_active_channel,
    get_channel_sources,
    add_channel_source,
    toggle_source,
    get_channel_drafts,
    get_draft,
    update_draft_text,
    update_draft_status,
    schedule_post,
    get_channel_stats,
    update_channel_prompt,
)
from inline_menu import (
    get_main_menu_keyboard,
    get_sources_keyboard,
    get_draft_keyboard,
    get_schedule_keyboard,
    get_channels_keyboard,
    get_settings_keyboard,
)
from keyboards import get_main_reply_keyboard
from datetime import datetime, timedelta

router = Router()
edit_states = {}


# ===========================
# 🚀 Global Menu Interceptor
# ===========================
@router.message(
    F.text.in_(
        {
            "📂 Выбрать канал",
            "📊 Статистика",
            "📰 Источники",
            "✏️ Черновики",
            "⚙️ Настройки",
            "❓ Помощь",
        }
    )
)
async def global_menu_interceptor(message: types.Message, state: FSMContext):
    await state.clear()

    if message.text == "📂 Выбрать канал":
        await handle_channels(message)
    elif message.text == "📊 Статистика":
        await handle_stats(message)
    elif message.text == "📰 Источники":
        await handle_sources(message)
    elif message.text == "✏️ Черновики":
        await handle_drafts(message)
    elif message.text == "⚙️ Настройки":
        await handle_settings(message)
    elif message.text == "❓ Помощь":
        await handle_help(message)


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
    await get_or_create_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )

    await message.answer(
        "🤖 <b>AI Content Bot</b>\n\n"
        "Автоматическая генерация постов для Telegram-каналов.\n\n"
        "Выбери раздел из меню внизу 👇",
        reply_markup=get_main_reply_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ===========================
# 📂 Channels
# ===========================


@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR)
)
async def bot_added_as_admin(event: ChatMemberUpdated):
    from database import add_channel, get_or_create_user

    user_id = event.from_user.id
    chat = event.chat

    await get_or_create_user(
        user_id, event.from_user.username, event.from_user.first_name
    )
    try:
        await add_channel(user_id, str(chat.id), chat.title)
        await event.bot.send_message(
            user_id,
            f"🎉 Бот добавлен в канал <b>{chat.title}</b> и готов к работе! Теперь выберите его в меню.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await event.bot.send_message(
            user_id, f"❌ Ошибка при автоматическом добавлении канала: {e}"
        )


async def handle_channels(message: types.Message):
    user = await get_user(message.from_user.id)
    channels = await get_user_channels(message.from_user.id)

    await message.answer(
        "📂 <b>Управление каналами</b>\n\nВыберите канал для работы:",
        reply_markup=get_channels_keyboard(
            channels, user.active_channel_id if user else None
        ),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "select_channel")
async def cb_select_channel(callback: types.CallbackQuery):
    user = await get_user(callback.from_user.id)
    channels = await get_user_channels(callback.from_user.id)

    await callback.message.edit_text(
        "📂 <b>Управление каналами</b>\n\nВыберите канал для работы:",
        reply_markup=get_channels_keyboard(
            channels, user.active_channel_id if user else None
        ),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("set_channel_"))
async def cb_set_channel(callback: types.CallbackQuery):
    channel_id = int(callback.data.split("_")[-1])

    # Ownership verification
    channels = await get_user_channels(callback.from_user.id)
    if not any(c.id == channel_id for c in channels):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await set_active_channel(callback.from_user.id, channel_id)

    channel = await get_channel(channel_id)
    await callback.answer(f"✅ Выбран канал: {channel.name}")
    await cb_select_channel(callback)


@router.callback_query(F.data == "add_channel")
async def cb_add_channel(callback: types.CallbackQuery, state: FSMContext):
    channels = await get_user_channels(callback.from_user.id)
    if len(channels) >= 5:
        await callback.answer("❌ Достигнут лимит (5 каналов).", show_alert=True)
        return

    await state.set_state(ChannelStates.waiting_for_name)
    await callback.message.answer(
        "📝 <b>Добавление канала</b>\n\n"
        "1. Отправь мне <b>название</b> твоего канала (например: <i>Мой Супер Канал</i>).\n\n"
        "Или отправь /cancel для отмены.",
        parse_mode=ParseMode.HTML,
    )


@router.message(ChannelStates.waiting_for_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    await state.update_data(channel_name=message.text.strip())
    await state.set_state(ChannelStates.waiting_for_id)
    await message.answer(
        "✅ Название принято.\n\n"
        "2. Теперь отправь <b>ID канала</b>.\n\n"
        "ℹ️ <i>Как узнать ID? Добавь бота в администраторы канала, а затем перешли любой пост из канала в этот чат. Бот напишет тебе ID.</i>\n\n"
        "Или просто введи ID вручную (обычно начинается с -100...)",
        parse_mode=ParseMode.HTML,
    )


@router.message(ChannelStates.waiting_for_id)
async def process_channel_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    channel_name = data["channel_name"]
    tg_channel_id = message.text.strip()

    # Простая проверка на формат ID
    if not tg_channel_id.startswith("-") or not tg_channel_id[1:].isdigit():
        # Если переслали сообщение, попробуем вытащить ID из forward_from_chat
        if message.forward_from_chat:
            tg_channel_id = str(message.forward_from_chat.id)
        else:
            await message.answer(
                "⚠️ Неверный формат ID. Он должен начинаться с -100... или просто перешли пост из канала."
            )
            return

    try:
        from database import add_channel

        channel = await add_channel(message.from_user.id, tg_channel_id, channel_name)
        await set_active_channel(message.from_user.id, channel.id)

        await message.answer(
            f"🎉 Канал <b>{channel_name}</b> успешно добавлен и выбран как активный!",
            reply_markup=get_main_reply_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении: {e}")
        await state.clear()


@router.callback_query(F.data == "delete_channel")
async def cb_delete_channel(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id:
        return

    await delete_channel(channel_id)
    await callback.answer("🗑 Канал удален", show_alert=True)
    await cb_select_channel(callback)


# ===========================
# 📊 Statistics
# ===========================


async def handle_stats(message: types.Message):
    channel_id = await get_active_channel_or_notify(message.from_user.id, message)
    if not channel_id:
        return

    stats = await get_channel_stats(channel_id)
    channel = await get_channel(channel_id)

    text = f"""
📊 <b>Статистика для {channel.name}</b>

📰 Источников активно: {stats["active_sources"]}

📝 Черновики:
• В ожидании: {stats["pending"]}
• Опубликованы: {stats["published"]}
• Пропущены: {stats["skipped"]}

📈 Всего создано: {stats["total_drafts"]}
"""
    await message.answer(text, parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "stats")
async def cb_stats(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id:
        return

    stats = await get_channel_stats(channel_id)
    channel = await get_channel(channel_id)

    text = f"""
📊 <b>Статистика для {channel.name}</b>

📰 Источников активно: {stats["active_sources"]}

📝 Черновики:
• В ожидании: {stats["pending"]}
• Опубликованы: {stats["published"]}
• Пропущены: {stats["skipped"]}

📈 Всего создано: {stats["total_drafts"]}
"""
    await callback.message.edit_text(
        text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML
    )


# ===========================
# 📰 Sources
# ===========================


async def handle_sources(message: types.Message):
    channel_id = await get_active_channel_or_notify(message.from_user.id, message)
    if not channel_id:
        return

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

    await message.answer(
        text,
        reply_markup=get_sources_keyboard(sources) if sources else None,
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "sources")
async def cb_sources(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id:
        return

    sources = await get_channel_sources(channel_id)
    channel = await get_channel(channel_id)

    if not sources:
        text = f"📰 В канале <b>{channel.name}</b> пока нет источников."
    else:
        text = f"📰 <b>Источники ({channel.name})</b>\n\n"
        for i, source in enumerate(sources, 1):
            status = "✅" if source.enabled else "❌"
            text += f"{status} {i}. {source.name}\n"

    await callback.message.edit_text(
        text, reply_markup=get_sources_keyboard(sources), parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("toggle_source_"))
async def cb_toggle_source(callback: types.CallbackQuery):
    source_id = int(callback.data.split("_")[-1])

    # We should technically check if this source belongs to active channel, but simplified here.
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id:
        return

    sources = await get_channel_sources(channel_id)
    source = next((s for s in sources if s.id == source_id), None)
    if source:
        await toggle_source(source_id, not source.enabled)

    await cb_sources(callback)


@router.callback_query(F.data == "add_source")
async def cb_add_source(callback: types.CallbackQuery, state: FSMContext):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id:
        return

    await state.set_state(SourceStates.waiting_for_name)
    await callback.message.answer(
        "📝 <b>Добавление источника</b>\n\n"
        "Отправь мне <b>название</b> источника (например: <i>Хабр ИИ</i>).\n\n"
        "Или отправь /cancel для отмены.",
        parse_mode=ParseMode.HTML,
    )


@router.message(SourceStates.waiting_for_name)
async def process_source_name(message: types.Message, state: FSMContext):
    await state.update_data(source_name=message.text.strip())
    await state.set_state(SourceStates.waiting_for_url)
    await message.answer(
        "✅ Принято. Теперь отправь <b>ссылку на RSS-ленту</b> (например: <i>https://habr.com/ru/rss/hub/ai/</i>).",
        parse_mode=ParseMode.HTML,
    )


@router.message(SourceStates.waiting_for_url)
async def process_source_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer(
            "⚠️ Ссылка должна начинаться с http или https. Попробуй еще раз."
        )
        return

    await state.update_data(source_url=url)
    await state.set_state(SourceStates.waiting_for_keywords)
    await message.answer(
        "✅ Принято. Теперь отправь <b>ключевые слова</b> через запятую.\n"
        "<i>Посты без этих слов будут игнорироваться.</i>\n\n"
        "Пример: <i>ии, нейросеть, chatgpt, ai</i>",
        parse_mode=ParseMode.HTML,
    )


@router.message(SourceStates.waiting_for_keywords)
async def process_source_keywords(message: types.Message, state: FSMContext):
    data = await state.get_data()
    channel_id = await get_active_channel_or_notify(message.from_user.id, message)

    if not channel_id:
        await state.clear()
        return

    try:
        await add_channel_source(
            channel_id=channel_id,
            name=data["source_name"],
            rss_url=data["source_url"],
            keywords=message.text.strip(),
        )
        await message.answer(
            f"🎉 Источник <b>{data['source_name']}</b> успешно добавлен!",
            reply_markup=get_main_reply_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при добавлении: {e}")
    finally:
        await state.clear()


# ===========================
# 📝 Drafts
# ===========================


async def handle_drafts(message: types.Message):
    channel_id = await get_active_channel_or_notify(message.from_user.id, message)
    if not channel_id:
        return

    drafts = await get_channel_drafts(channel_id, limit=5)

    if not drafts:
        await message.answer(
            "📭 У тебя пока нет активных черновиков.", parse_mode=ParseMode.HTML
        )
        return

    await message.answer(
        f"📝 <b>Последние черновики ({len(drafts)} шт.):</b>", parse_mode=ParseMode.HTML
    )

    for draft in drafts:
        status_emoji = {
            "pending": "⏳",
            "published": "✅",
            "skipped": "❌",
            "scheduled": "⏰",
        }
        status = status_emoji.get(draft.status, "📄")

        text = f"""
{status} <b>{draft.title}</b>
━━━━━━━━━━━━━━━━
{draft.post_text}

━━━━━━━━━━━━━━━━
🔗 Источник: {draft.source_name}
🆔 ID: {draft.id}
"""
        if draft.image_url:
            text += "\n🖼️ Картинка: Прикреплена"
            await message.answer_photo(
                photo=draft.image_url,
                caption=text.strip(),
                reply_markup=get_draft_keyboard(draft.id),
                parse_mode=ParseMode.HTML,
            )
        else:
            await message.answer(
                text=text.strip(),
                reply_markup=get_draft_keyboard(draft.id),
                parse_mode=ParseMode.HTML,
            )


@router.callback_query(F.data == "drafts")
async def cb_drafts(callback: types.CallbackQuery):
    channel_id = (
        await get_active_channel_or_notify(callback.fromuser.id, callback)
        if hasattr(callback, "from_user")
        else await get_active_channel_or_notify(callback.from_user.id, callback)
    )
    if not channel_id:
        return

    drafts = await get_channel_drafts(channel_id, limit=5)

    if not drafts:
        text = "📭 Нет активных черновиков"
    else:
        text = "📝 <b>Последние черновики</b>\n\n"
        for draft in drafts:
            status_emoji = {
                "pending": "⏳",
                "published": "✅",
                "skipped": "❌",
                "scheduled": "⏰",
            }
            text += f"{status_emoji.get(draft.status)} {draft.title[:50]}...\n"

    await callback.message.edit_text(
        text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML
    )


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
                parse_mode=ParseMode.HTML,
            )
        else:
            await callback.bot.send_message(
                chat_id=channel.tg_channel_id,
                text=draft.post_text,
                parse_mode=ParseMode.HTML,
            )
        await update_draft_status(draft_id, "published")
        await callback.answer("✅ Опубликовано в канал!", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        await callback.answer(f"❌ Ошибка публикации: {e}", show_alert=True)


@router.callback_query(F.data.startswith("pre_schedule_"))
async def cb_pre_schedule(callback: types.CallbackQuery):
    draft_id = int(callback.data.split("_")[-1])
    await callback.message.edit_reply_markup(
        reply_markup=get_schedule_keyboard(draft_id)
    )


@router.callback_query(F.data.startswith("do_schedule_"))
async def cb_do_schedule(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    draft_id = int(parts[2])
    hours = int(parts[3])

    draft = await get_draft(draft_id)
    if not draft:
        return

    scheduled_time = datetime.now() + timedelta(hours=hours)
    await schedule_post(draft.channel_id, draft_id, scheduled_time)

    await callback.answer(
        f"📅 Запланировано на {scheduled_time.strftime('%H:%M %d.%m')}", show_alert=True
    )
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("edit_draft_"))
async def cb_edit_draft(callback: types.CallbackQuery, state: FSMContext):
    draft_id = int(callback.data.split("_")[-1])
    await state.update_data(draft_id=draft_id)
    await state.set_state(DraftStates.waiting_for_text)

    await callback.message.answer(
        "✏️ Отправь новый текст черновика:\n\nИли /cancel для отмены"
    )


@router.message(DraftStates.waiting_for_text)
async def process_draft_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    draft_id = data.get("draft_id")

    if not draft_id:
        await state.clear()
        return

    try:
        await update_draft_text(draft_id, message.text)
        await message.answer(
            "✅ Текст обновлён!", reply_markup=get_draft_keyboard(draft_id)
        )
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при обновлении: {e}")
    finally:
        await state.clear()


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("📭 Нет активного действия")
        return

    await state.clear()
    await message.answer("✖️ Отменено", reply_markup=get_main_reply_keyboard())


# ===========================
# ⚙️ Settings
# ===========================


async def handle_settings(message: types.Message):
    channel_id = await get_active_channel_or_notify(message.from_user.id, message)
    if not channel_id:
        return
    await message.answer("⚙️ Настройки канала:", reply_markup=get_settings_keyboard())


@router.callback_query(F.data == "edit_prompt")
async def cb_edit_prompt(callback: types.CallbackQuery, state: FSMContext):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id:
        return

    from database import get_channel

    channel = await get_channel(channel_id)

    await state.set_state(ChannelStates.waiting_for_prompt)
    await callback.message.answer(
        f"📝 <b>Кастомный промпт для канала {channel.name}</b>\n\n"
        f"Текущий промпт:\n<i>{channel.custom_prompt or 'Не задан'}</i>\n\n"
        "Отправьте новый текст правил для нейросети (например: 'Пиши от лица программиста, используй сленг').\n"
        "Или отправьте /cancel для отмены.",
        parse_mode=ParseMode.HTML,
    )


@router.message(ChannelStates.waiting_for_prompt)
async def process_channel_prompt(message: types.Message, state: FSMContext):
    channel_id = await get_active_channel_or_notify(message.from_user.id, message)
    if not channel_id:
        await state.clear()
        return

    await update_channel_prompt(channel_id, message.text.strip())
    await message.answer(
        "✅ Кастомный промпт успешно сохранен!", reply_markup=get_main_reply_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "settings")
async def cb_settings(callback: types.CallbackQuery):
    channel_id = await get_active_channel_or_notify(callback.from_user.id, callback)
    if not channel_id:
        return
    await callback.message.edit_text(
        "⚙️ Настройки канала:", reply_markup=get_settings_keyboard()
    )


# ===========================
# ❓ Help
# ===========================


async def handle_help(message: types.Message):
    text = """
❓ <b>Справка по боту</b>

Бот предназначен для автоматизации ведения Telegram каналов.
1. Добавьте канал (бот должен быть администратором в канале).
2. Добавьте RSS/Atom источники.
3. Бот будет парсить новости, переписывать их через нейросеть и сохранять в Черновики.
4. Вы можете публиковать их вручную или настроить автопостинг.
"""
    await message.answer(text, parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "help")
async def cb_help(callback: types.CallbackQuery):
    text = """
❓ <b>Справка по боту</b>

Бот предназначен для автоматизации ведения Telegram каналов.
1. Добавьте канал (бот должен быть администратором в канале).
2. Добавьте RSS/Atom источники.
3. Бот будет парсить новости, переписывать их через нейросеть и сохранять в Черновики.
4. Вы можете публиковать их вручную или настроить автопостинг.
"""
    await callback.message.edit_text(
        text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML
    )


# ===========================
# 💳 Subscribe & Navigation
# ===========================


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )
