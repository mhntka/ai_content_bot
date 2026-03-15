import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from scheduler import start_scheduler
from handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(router)
    
    scheduler = start_scheduler()
    
    print("🚀 Бот запущен!")
    print("💡 Используй /start для начала")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())