import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, REDIS_URL
from database import init_db
from scheduler import start_scheduler
from handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()

    bot = Bot(token=BOT_TOKEN)

    # Пытаемся подключить Redis, если нет - используем память
    try:
        from aiogram.fsm.storage.redis import RedisStorage
        from redis.asyncio import Redis

        redis = Redis.from_url(REDIS_URL)
        storage = RedisStorage(redis=redis)
        logging.info("✅ Подключен Redis для FSM")
    except Exception as e:
        logging.warning(f"⚠️ Redis недоступен, используем память (MemoryStorage): {e}")
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    dp.include_router(router)

    start_scheduler()

    print("🚀 Бот запущен!")
    print("Отправь команду /start для начала")

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())