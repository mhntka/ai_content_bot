"""
🎛️ Handlers — кнопки и команды для модерации черновиков
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_draft, update_draft_text, delete_draft, publish_draft, mark_published
from config import CHANNEL_ID, BOT_TOKEN

router = Router()

# Храним состояние редактирования: {user_id: draft_id}
edit_state = {}


def get_draft_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    """Кнопки для черновика"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve_{draft_id}"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{draft_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Пропустить", callback_data=f"skip_{draft_id}")
        ]
    ])


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 Бот-контент менеджер запущен!\n\n"
        "📬 Черновики приходят сюда\n"
        "✅ Кнопки: Опубликовать / Редактировать / Пропустить\n\n"
        "Команды:\n"
        "/status - статистика\n"
        "/drafts - активные черновики"
    )


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Статистика по черновикам"""
    import aiosqlite
    from config import DB_NAME
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM drafts WHERE status = 'pending'")
        pending = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM drafts WHERE status = 'published'")
        published = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM drafts WHERE status = 'skipped'")
        skipped = (await cursor.fetchone())[0]
    
    await message.answer(
        f"📊 Статистика:\n\n"
        f"⏳ В ожидании: {pending}\n"
        f"✅ Опубликованы: {published}\n"
        f"❌ Пропущены: {skipped}"
    )


@router.message(Command("drafts"))
async def cmd_drafts(message: types.Message):
    """Показать активные черновики"""
    import aiosqlite
    from config import DB_NAME
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM drafts WHERE status = 'pending' ORDER BY created_at DESC LIMIT 5"
        )
        drafts = await cursor.fetchall()
    
    if not drafts:
        await message.answer("📭 Нет активных черновиков")
        return
    
    for draft in drafts:
        text = f"📝 **Черновик #{draft['id']}**\n\n{draft['post_text'][:500]}..."
        keyboard = get_draft_keyboard(draft['id'])
        await message.answer(text, parse_mode='Markdown', reply_markup=keyboard)


@router.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: types.CallbackQuery):
    """Пользователь одобрил черновик → публикуем в канал"""
    draft_id = int(callback.data.split("_")[1])
    
    draft = await get_draft(draft_id)
    if not draft:
        await callback.answer("❌ Черновик не найден", show_alert=True)
        return
    
    try:
        bot = Bot(token=BOT_TOKEN)
        
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=draft['post_text'],
            parse_mode='Markdown'
        )
        
        await publish_draft(draft_id)
        await mark_published(draft['source_url'])
        
        await callback.answer("✅ Опубликовано в канале!", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        
        await bot.session.close()
        await bot.close()
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data.startswith("edit_"))
async def cb_edit(callback: types.CallbackQuery):
    """Пользователь хочет редактировать"""
    draft_id = int(callback.data.split("_")[1])
    
    edit_state[callback.from_user.id] = draft_id
    
    await callback.answer("✏️ Отправь новый текст сообщения", show_alert=True)
    await callback.message.answer(
        "📝 Отправь мне отредактированный текст поста.\n\n"
        "Я сохраню его и покажу кнопки снова.\n\n"
        "Или напиши /cancel чтобы отменить"
    )


@router.message(F.text)
async def handle_edit_text(message: types.Message):
    """Пользователь прислал отредактированный текст"""
    user_id = message.from_user.id
    
    if user_id not in edit_state:
        return
    
    draft_id = edit_state[user_id]
    new_text = message.text
    
    await update_draft_text(draft_id, new_text)
    
    keyboard = get_draft_keyboard(draft_id)
    await message.answer(
        f"✅ Текст обновлён!\n\n{new_text[:500]}...",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    del edit_state[user_id]


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    """Отмена редактирования"""
    user_id = message.from_user.id
    
    if user_id in edit_state:
        del edit_state[user_id]
        await message.answer("✖️ Редактирование отменено")
    else:
        await message.answer("📭 Нет активного редактирования")


@router.callback_query(F.data.startswith("skip_"))
async def cb_skip(callback: types.CallbackQuery):
    """Пользователь пропустил черновик"""
    draft_id = int(callback.data.split("_")[1])
    
    await delete_draft(draft_id)
    await callback.answer("❌ Пропущено", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)


# Импорты внутри функций (чтобы избежать циклического импорта)
from aiogram import Bot