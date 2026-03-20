FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
# Убедимся, что все важные пакеты на месте
RUN pip install --no-cache-dir sqlalchemy asyncpg alembic python-dotenv aioredis redis groq openai anthropic

COPY . .

# Удаляем файл-скрипт, если он есть, чтобы не мешался
RUN rm -f docker-entrypoint.sh

# Запуск прямо в CMD: ждем БД, делаем миграции и стартуем
CMD sh -c "echo '⏳ Ожидание базы данных...' && \
    until pg_isready -h db -U postgres; do sleep 1; done && \
    echo '✅ База данных готова!' && \
    echo '🚀 Применение миграций...' && \
    alembic upgrade head && \
    echo '🤖 Запуск бота...' && \
    python main.py"
