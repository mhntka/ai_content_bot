import asyncio
import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from parser import parse_all_for_user
from ai_writer import generate_post
from database import (
    is_published, mark_published, save_draft, get_user_sources,
    get_or_create_user, get_due_scheduled_posts, mark_scheduled_published,
    check_subscription
)
from config import POST_INTERVAL_MIN, POST_INTERVAL_MAX, BOT_TOKEN, DB_NAME
from aiogram import Bot
import aiosqlite

bot = Bot(token=BOT_TOKEN)

async def publish_for_user(user_id: int):
    """Генерация и отправка черновика для одного пользователя"""
    
    # Проверяем подписку
    sub = await check_subscription(user_id)
    if not sub['active']:
        return
    
    # Парсинг
    articles = await parse_all_for_user(user_id)
    
    if not articles:
        return
    
    # Берём первую новую
    article = None
    for a in articles:
        if not await is_published(user_id, a['url']):
            article = a
            break
    
    if not article:
        return
    
    # Генерация
    result = await generate_post(
        title=article['title'],
        source_url=article['url'],
        lang=article.get('lang', 'en'),
        summary=article.get('summary', ''),
        source_name=article.get('source', '')
    )
    
    if not result['success']:
        return
    
    # Сохраняем черновик
    draft_id = await save_draft(
        user_id=user_id,
        source_url=article['url'],
        text=result['text'],
        title=article['title'],
        source_name=article.get('source', ''),
        style=result.get('style', '')
    )
    
    # Отправляем пользователю
    from inline_menu import get_draft_keyboard
    
    draft_text = f"""
📝 **НОВЫЙ ЧЕРНОВИК #{draft_id}**
━━━━━━━━━━━━━━━━
{result['text']}

━━━━━━━━━━━━━━━━
🔗 Источник: {article['url']}
🏷️ Стиль: {result.get('style', 'unknown')}
"""
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=draft_text.strip(),
            reply_markup=get_draft_keyboard(draft_id),
            parse_mode='Markdown'
        )
        
        await mark_published(user_id, article['url'])
        
    except Exception as e:
        print(f"❌ Ошибка отправки пользователю {user_id}: {e}")

async def check_scheduled_posts_job():
    """Фоновая задача для публикации запланированных постов"""
    due_posts = await get_due_scheduled_posts()
    
    for post in due_posts:
        try:
            if not post['target_channel_id']:
                print(f"⚠️ У пользователя {post['user_id']} не привязан канал для поста #{post['draft_id']}")
                continue
                
            await bot.send_message(
                chat_id=post['target_channel_id'],
                text=post['post_text'],
                parse_mode='Markdown'
            )
            
            await mark_scheduled_published(post['sched_id'])
            print(f"✅ Запланированный пост #{post['draft_id']} опубликован в {post['target_channel_id']}")
            
        except Exception as e:
            print(f"❌ Ошибка публикации запланированного поста {post['sched_id']}: {e}")

async def publish_for_all_users():
    """Генерация черновиков для всех активных пользователей"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT telegram_id FROM users WHERE subscription_status != 'inactive'"
        )
        users = await cursor.fetchall()
    
    tasks = [publish_for_user(user['telegram_id']) for user in users]
    await asyncio.gather(*tasks, return_exceptions=True)

def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    # Интервал генерации новых черновиков
    scheduler.add_job(
        publish_for_all_users,
        trigger=IntervalTrigger(minutes=random.randint(POST_INTERVAL_MIN, POST_INTERVAL_MAX)),
        id='content_publisher',
        replace_existing=True
    )
    
    # Проверка запланированных постов каждую минуту
    scheduler.add_job(
        check_scheduled_posts_job,
        trigger='interval',
        minutes=1,
        id='scheduled_publisher'
    )
    
    scheduler.start()
    print("⏰ Планировщик запущен: генерация черновиков и публикация по расписанию.")
    return scheduler