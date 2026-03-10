import asyncio
import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from parser import parse_all
from ai_writer import generate_post
from database import is_published, mark_published, save_draft
from config import POST_INTERVAL_MIN, POST_INTERVAL_MAX, BOT_TOKEN
from aiogram import Bot
from handlers import get_draft_keyboard

bot = Bot(token=BOT_TOKEN)

async def publish_post():
    """
    Задача: найти статью → сгенерировать → отправить АДМИНУ в личку с кнопками
    """
    print("🔄 Запуск генерации черновика...")
    
    # 1. Парсинг
    articles = await parse_all()
    new_articles = [a for a in articles if not await is_published(a['url'])]
    
    if not new_articles:
        print("📭 Новых статей нет, пропускаю")
        return
    
    # 2. Берём первую новую
    article = new_articles[0]
    print(f"📰 Статья: {article['title'][:60]}...")
    
    # 3. Генерация
    result = await generate_post(
        title=article['title'],
        source_url=article['url'],
        lang=article.get('lang', 'en'),
        summary=article.get('summary', ''),
        source_name=article.get('source', '')
    )
    
    if not result['success']:
        print(f"❌ Ошибка генерации: {result['error']}")
        return
    
    print(f"✅ Пост сгенерирован (стиль: {result.get('style', 'unknown')})")
    
    # 4. Сохраняем черновик в БД
    draft_id = await save_draft(
        url=article['url'],
        text=result['text'],
        title=article['title'],
        source=article.get('source', '')
    )
    
    # 5. Отправляем АДМИНУ в личку (не в канал!)
    admin_id = None
    try:
        # Получаем ID первого владельца бота
        me = await bot.get_me()
        # Для простоты - шлём тому, кто запустил бота последним
        # В продакшене лучше захардкодить admin_id в config.py
        from config import ADMIN_ID
        admin_id = ADMIN_ID
    except:
        print("❌ Не удалось получить ADMIN_ID")
        return
    
    if not admin_id:
        print("❌ ADMIN_ID не указан в config.py")
        return
    
    try:
        keyboard = get_draft_keyboard(draft_id)
        
        await bot.send_message(
            chat_id=admin_id,
            text=f"📝 НОВЫЙ ЧЕРНОВИК #{draft_id}\n\n{result['text']}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        print(f"✅ Черновик #{draft_id} отправлен админу")
        
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")


def get_random_interval():
    minutes = random.randint(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
    return minutes / 60


def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    scheduler.add_job(
        publish_post,
        trigger=IntervalTrigger(hours=get_random_interval()),
        id='content_publisher',
        replace_existing=True,
        misfire_grace_time=300
    )
    
    scheduler.start()
    print(f"⏰ Планировщик запущен: посты каждые {POST_INTERVAL_MIN//60}-{POST_INTERVAL_MAX//60} часов")
    return scheduler