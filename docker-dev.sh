#!/bin/bash

# Скрипт для запуска только базы данных в режиме разработки

set -e

echo "🔧 Запуск инфраструктуры для разработки..."

# Запускаем только базу данных и Redis
echo "🚀 Запуск PostgreSQL и Redis..."
docker-compose up -d postgres redis

# Ждем готовности
echo "⏳ Ожидание готовности сервисов..."
sleep 5

# Проверяем статус
echo "📊 Статус сервисов:"
docker-compose ps postgres redis

echo ""
echo "✅ Инфраструктура готова для разработки!"
echo ""
echo "📋 Настройте переменные окружения:"
echo "   export DATABASE_URL='postgresql://article_bot:article_bot_password@localhost:5432/article_bot'"
echo "   export REDIS_URL='redis://localhost:6379/0'"
echo "   export ARTICLE_BOT_TOKEN='your_bot_token'"
echo ""
echo "🚀 Запустите приложение локально:"
echo "   python simple_bot.py    # Только бот"
echo "   python api_server.py    # Только API"
echo "   python main_bot.py      # Бот + API"
echo ""
echo "📋 Полезные команды:"
echo "   docker-compose logs -f postgres  # Логи PostgreSQL"
echo "   docker-compose logs -f redis     # Логи Redis"
echo "   docker-compose down              # Остановка"
