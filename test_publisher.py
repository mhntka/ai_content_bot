"""
🧪 Тест полной цепочки: Парсинг → Генерация → Черновик в канал
Отправляет пост в DRAFT_CHANNEL_ID (если задан) или в CHANNEL_ID
"""

import asyncio
import re
from aiogram import Bot
from parser import parse_all
from ai_writer import generate_post
from database import is_published, mark_published, init_db
from config import BOT_TOKEN, CHANNEL_ID, DRAFT_CHANNEL_ID


async def test():
    print("🔄 Запуск полной цепочки (режим черновиков)...\n")
    
    # Инициализация БД
    await init_db()
    
    # 1. 🔍 Парсинг всех источников
    print("📡 Сканирую источники...")
    articles = await parse_all()
    print(f"📰 Найдено статей: {len(articles)}\n")
    
    if not articles:
        print("❌ Статьи не найдены")
        print("💡 Проверь: интернет, RSS-ссылки, ключевые слова в config.py")
        return
    
    # 2. 🎯 Берём первую новую статью (не опубликованную ранее)
    article = None
    for a in articles:
        if not await is_published(a['url']):
            article = a
            break
    
    if not article:
        print("⚠️ Все найденные статьи уже обработаны")
        print("💡 Удали content_bot.db для полного сброса")
        return
        
    print(f"📄 Выбрана статья:")
    print(f"   Заголовок: {article['title'][:70]}...")
    print(f"   Источник: {article['source']} ({article['lang']})")
    print(f"   URL: {article['url']}\n")
    
    # 3. 🤖 Генерация поста (с ротацией стилей)
    print("✍️ Генерирую пост...")
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
    
    print("✅ Пост сгенерирован:\n")
    print("─" * 40)
    print(result['text'])
    print("─" * 40 + "\n")
    
    # 4. 📝 Формируем черновик с мета-информацией
    draft_text = f"""
📝 ЧЕРНОВИК ПОСТА
━━━━━━━━━━━━━━━━
{result['text']}

━━━━━━━━━━━━━━━━
🔗 Источник: {article['url']}
🏷️ Стиль: {result.get('style', 'unknown')}
🌐 Язык оригинала: {article.get('lang', 'en')}
🤖 Сгенерировано автоматически
✏️ Отредактируй и опубликуй вручную
"""
    
    # 5. 📤 Определяем канал для отправки
    target_channel = DRAFT_CHANNEL_ID or CHANNEL_ID
    channel_type = "черновиков" if DRAFT_CHANNEL_ID else "основной"
    
    if not target_channel:
        print("❌ Ошибка: не указан ни CHANNEL_ID, ни DRAFT_CHANNEL_ID")
        print("💡 Проверь файл .env")
        return
    
    print(f"📤 Отправляю черновик в {channel_type} канал ({target_channel})...")
    
    # 6. 🤖 Отправка через aiogram
    bot = Bot(token=BOT_TOKEN)
    
    try:
        await bot.send_message(
            chat_id=target_channel,
            text=draft_text.strip(),
            parse_mode='Markdown'
        )
        print("✅ Черновик успешно отправлен!")
        
        # Помечаем статью как обработанную
        await mark_published(article['url'])
        print("🗄️ Статья сохранена в БД (не будет дублей)")
        
    except Exception as e:
        error_msg = str(e)
        if "Flood control" in error_msg or "Too Many Requests" in error_msg:
            print("⏳ Telegram: лимит запросов. Подожди 10 минут и попробуй снова.")
        elif "Forbidden" in error_msg:
            print("❌ Ошибка прав: добавь бота в канал как админа с правом публикации")
        elif "Bad Request: chat not found" in error_msg:
            print(f"❌ Канал не найден: проверь ID {target_channel}")
        else:
            print(f"❌ Ошибка отправки: {error_msg}")
    
    finally:
        # Безопасное закрытие сессии
        try:
            await bot.session.close()
        except:
            pass
        try:
            await bot.close()
        except:
            pass
    
    print("\n🎉 Тест завершён!")
    print("💡 Проверь канал — черновик должен прийти в течение 1-2 секунд")


if __name__ == "__main__":
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()