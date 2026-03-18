import asyncio
import random
import aiohttp
import os
from urllib.parse import quote
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from parser import parse_all_for_user
from ai_writer import generate_post
from database import (
    is_published, mark_published, save_draft, get_channel_sources,
    get_or_create_user, get_due_scheduled_posts, mark_scheduled_published,
    check_subscription, get_user_channels, get_channel
)
from config import POST_INTERVAL_MIN, POST_INTERVAL_MAX, BOT_TOKEN
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from database import async_session
from sqlalchemy import select
from aiogram import Bot
from aiogram.enums import ParseMode

bot = Bot(token=BOT_TOKEN)

async def fetch_unsplash_image(query: str) -> str:
    """Запрашивает случайную картинку с Unsplash по ключевому слову."""
    api_key = os.getenv('UNSPLASH_ACCESS_KEY')
    if not api_key or not query:
        return None
        
    url = f"https://api.unsplash.com/photos/random?query={quote(query)}&orientation=landscape"
    headers = {"Authorization": f"Client-ID {api_key}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['urls']['regular']
                return None
    except Exception as e:
        print(f"⚠️ Ошибка Unsplash: {e}")
        return None

async def publish_for_channel(channel_id: int, user_id: int):
    """Генерация и отправка черновика для одного канала"""
    
    # Парсинг (мы переделаем parse_all_for_user под канал)
    from parser import parse_rss_source
    sources = await get_channel_sources(channel_id)
    if not sources:
        return
        
    all_articles = []
    for source in sources:
        if source.enabled:
            articles = await parse_rss_source(source)
            all_articles.extend(articles)
            
    all_articles.sort(key=lambda x: x['published'], reverse=True)
    
    if not all_articles:
        return
    
    # Берём первую новую
    article = None
    for a in all_articles:
        if not await is_published(channel_id, a['url']):
            article = a
            break
    
    if not article:
        return
    
    # Генерация текста
    result = await generate_post(
        title=article['title'],
        source_url=article['url'],
        lang=article.get('lang', 'en'),
        summary=article.get('summary', ''),
        source_name=article.get('source', '')
    )
    
    if not result['success']:
        return
        
    # Изображения: если нет оригинального, ищем на Unsplash
    image_url = article.get('image_url')
    if not image_url:
        search_query = 'artificial intelligence' # Fallback query
        if 'ai' in article['title'].lower() or 'ии' in article['title'].lower():
            search_query = 'technology ai'
        image_url = await fetch_unsplash_image(search_query)
    
    # Сохраняем черновик
    draft_id = await save_draft(
        channel_id=channel_id,
        source_url=article['url'],
        text=result['text'],
        title=article['title'],
        source_name=article.get('source', ''),
        style=result.get('style', ''),
        image_url=image_url
    )
    
    # Отправляем пользователю (уведомление о черновике)
    from inline_menu import get_draft_keyboard
    channel = await get_channel(channel_id)
    
    draft_text = f"""
📝 <b>НОВЫЙ ЧЕРНОВИК #{draft_id} ({channel.name})</b>
━━━━━━━━━━━━━━━━
{result['text']}

━━━━━━━━━━━━━━━━
🔗 Источник: {article['url']}
🏷️ Стиль: {result.get('style', 'unknown')}
"""
    
    try:
        if image_url:
            await bot.send_photo(
                chat_id=user_id,
                photo=image_url,
                caption=draft_text.strip(),
                reply_markup=get_draft_keyboard(draft_id),
                parse_mode='HTML'
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=draft_text.strip(),
                reply_markup=get_draft_keyboard(draft_id),
                parse_mode='HTML'
            )
        
        await mark_published(channel_id, article['url'])
        
    except Exception as e:
        print(f"❌ Ошибка отправки пользователю {user_id}: {e}")

async def check_scheduled_posts_job():
    """Фоновая задача для публикации запланированных постов"""
    due_posts = await get_due_scheduled_posts()
    
    for post in due_posts:
        try:
            if not post['target_channel_id']:
                continue
                
            if post.get('image_url'):
                await bot.send_photo(
                    chat_id=post['target_channel_id'],
                    photo=post['image_url'],
                    caption=post['post_text'],
                    parse_mode='HTML'
                )
            else:
                await bot.send_message(
                    chat_id=post['target_channel_id'],
                    text=post['post_text'],
                    parse_mode='HTML'
                )
            
            await mark_scheduled_published(post['sched_id'])
            print(f"✅ Запланированный пост #{post['draft_id']} опубликован в {post['target_channel_id']}")
            
        except Exception as e:
            print(f"❌ Ошибка публикации запланированного поста {post['sched_id']}: {e}")

async def publish_for_all_users():
    """Генерация черновиков для всех каналов активных пользователей"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.subscription_status != 'inactive')
        )
        users = result.scalars().all()
    
    tasks = []
    for user in users:
        channels = await get_user_channels(user.telegram_id)
        for channel in channels:
            tasks.append(publish_for_channel(channel.id, user.telegram_id))
            
    if tasks:
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