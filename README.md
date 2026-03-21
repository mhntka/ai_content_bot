# AI Content Bot

Telegram-бот для автоматической генерации и публикации контента в ваши каналы с использованием нейросетей.

## Основные возможности

- **Многоканальность:** Поддержка управления контентом до 5 Telegram-каналов одновременно.
- **Генерация текста:** Использование мощных моделей искусственного интеллекта (Groq API, LLaMA 3) для создания качественных постов.
- **Поиск изображений:** Автоматический подбор подходящих фотографий к постам через Unsplash API.
- **Отложенный постинг:** Встроенный планировщик задач для публикации контента по расписанию.
- **Удобное управление:** Интерактивное inline-меню прямо в Telegram для настройки бота и управления каналами.
- **Надежность:** Использование базы данных PostgreSQL (через SQLAlchemy ORM) для хранения настроек и состояния.
- **Простое развертывание:** Полная контейнеризация с помощью Docker и docker-compose.

## Требования

Для запуска бота вам потребуется:
- Установленный [Docker](https://www.docker.com/) и [Docker Compose](https://docs.docker.com/compose/).
- Токен Telegram бота (получить у [@BotFather](https://t.me/BotFather)).
- API ключ Groq (для генерации текста).
- Access Key Unsplash (для поиска картинок).

## Установка и запуск (через Docker)

1. **Клонируйте репозиторий (если у вас его еще нет):**
   ```bash
   git clone https://github.com/mhntka/ai_content_bot.git
   cd ai_content_bot
   ```

2. **Настройте переменные окружения:**
   Скопируйте файл-пример `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```
   Откройте файл `.env` в любом текстовом редакторе и заполните ваши данные:
   ```ini
   # Токен вашего Telegram бота
   BOT_TOKEN=ваш_токен_от_botfather
   
   # Ваш Telegram ID (для доступа к админке бота)
   ADMIN_ID=ваш_telegram_id
   
   # Ключ от Groq API
   GROQ_API_KEY=ваш_ключ_groq
   GROQ_MODEL=llama-3.1-8b-instant
   
   # Настройки базы данных 
   # 🛡️ ВАЖНО: Укажите надежный пароль вместо "your_secure_password" в обеих строках ниже!
   POSTGRES_PASSWORD=your_secure_password
   DATABASE_URL=postgresql+asyncpg://postgres:your_secure_password@db:5432/ai_content_bot
   
   # Ключ от Unsplash
   UNSPLASH_ACCESS_KEY=ваш_ключ_unsplash
   ```

3. **Запустите проект:**
   Используйте docker-compose для сборки и запуска контейнеров в фоновом режиме:
   ```bash
   docker-compose up -d --build
   ```

4. **Применение миграций базы данных:**
   После успешного запуска контейнеров, необходимо создать таблицы в базе данных:
   ```bash
   docker-compose exec bot alembic upgrade head
   ```

Бот запущен и готов к работе! Напишите ему `/start` в Telegram.

## Как получить API ключи

### Telegram Bot Token
1. Напишите в Telegram боту [@BotFather](https://t.me/BotFather).
2. Отправьте команду `/newbot`, придумайте имя и юзернейм для вашего бота.
3. Скопируйте полученный токен.

### Узнать свой Telegram ID (ADMIN_ID)
1. Напишите боту [@userinfobot](https://t.me/userinfobot) или [@GetMyIDBot](https://t.me/getmyid_bot).
2. Скопируйте ваш `ID` (это набор цифр).

### Groq API Key
1. Зарегистрируйтесь на сайте [Groq Console](https://console.groq.com/).
2. Перейдите в раздел "API Keys" и создайте новый ключ.

### Unsplash API Key
1. Зарегистрируйтесь на [Unsplash Developers](https://unsplash.com/developers).
2. Нажмите "New Application", примите правила.
3. В настройках созданного приложения скопируйте `Access Key`.

## Локальная разработка (без Docker)
1. Установите Python 3.10+ и PostgreSQL.
2. Создайте виртуальное окружение: `python -m venv venv`
3. Активируйте его: `venv\Scripts\activate` (Windows) или `source venv/bin/activate` (Linux/Mac).
4. Установите зависимости: `pip install -r requirements.txt`
5. Настройте файл `.env` (не забудьте указать правильный `DATABASE_URL` для вашей локальной БД).
6. Примените миграции: `alembic upgrade head`
7. Запустите бота: `python main.py`
