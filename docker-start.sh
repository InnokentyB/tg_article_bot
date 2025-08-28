#!/bin/bash

# Скрипт для запуска Telegram Article Bot в Docker

set -e

echo "🚀 Запуск Telegram Article Bot..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Создаем из примера..."
    cp env.example .env
    echo "📝 Отредактируйте .env файл и добавьте ваш Telegram Bot Token"
    echo "   Затем запустите скрипт снова"
    exit 1
fi

# Проверяем переменные окружения
source .env

if [ -z "$ARTICLE_BOT_TOKEN" ] || [ "$ARTICLE_BOT_TOKEN" = "your_telegram_bot_token_here" ]; then
    echo "❌ Ошибка: ARTICLE_BOT_TOKEN не настроен в .env файле"
    echo "   Получите токен у @BotFather и добавьте в .env файл"
    exit 1
fi

echo "✅ Конфигурация проверена"

# Останавливаем существующие контейнеры
echo "🛑 Остановка существующих контейнеров..."
docker-compose down

# Собираем образы
echo "🔨 Сборка Docker образов..."
docker-compose build

# Запускаем сервисы
echo "🚀 Запуск сервисов..."
docker-compose up -d

# Ждем готовности базы данных
echo "⏳ Ожидание готовности базы данных..."
sleep 10

# Проверяем статус
echo "📊 Статус сервисов:"
docker-compose ps

echo ""
echo "✅ Telegram Article Bot запущен!"
echo ""
echo "🌐 API доступен по адресу: http://localhost:5000"
echo "📱 Telegram бот готов к работе"
echo ""
echo "📋 Полезные команды:"
echo "   docker-compose logs -f bot    # Логи бота"
echo "   docker-compose logs -f api    # Логи API"
echo "   docker-compose down           # Остановка"
echo "   docker-compose restart bot    # Перезапуск бота"
