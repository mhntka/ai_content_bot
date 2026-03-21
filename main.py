import asyncio
import logging
from logging.handlers import RotatingFileHandler
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from config import BOT_TOKEN, REDIS_URL
from database import init_db
from scheduler import start_scheduler
from handlers import router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler("bot.log", maxBytes=5000000, backupCount=3, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    await init_db()

    bot = Bot(token=BOT_TOKEN)

    # Пытаемся подключить Redis, если нет - используем память
    try:
        from aiogram.fsm.storage.redis import RedisStorage
        from redis.asyncio import Redis

        redis = Redis.from_url(REDIS_URL)
        storage = RedisStorage(redis=redis)
        logger.info("✅ Подключен Redis для FSM")
    except Exception as e:
        logger.warning(f"⚠️ Redis недоступен, используем память (MemoryStorage): {e}")
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # Глобальный обработчик ошибок
    @dp.errors()
    async def global_error_handler(event: ErrorEvent):
        logger.exception(f"Exception while handling an update: {event.exception}")
        # Здесь можно добавить отправку уведомления админу (вам)
        pass

    dp.include_router(router)

    start_scheduler()

    logger.info("🚀 Бот запущен!")
    print("Отправь команду /start для начала")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
