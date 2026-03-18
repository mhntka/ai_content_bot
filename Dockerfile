FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir sqlalchemy asyncpg alembic python-dotenv

COPY . .

# Скрипт запуска для применения миграций перед стартом
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'alembic upgrade head' >> /entrypoint.sh && \
    echo 'python main.py' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
