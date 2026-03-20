#!/bin/sh
set -e

echo "⏳ Ожидание базы данных..."
while ! pg_isready -h db -U postgres; do
  sleep 1
done

echo "✅ База данных готова!"
echo "🚀 Применение миграций..."
alembic upgrade head

echo "🤖 Запуск бота..."
exec python main.py
