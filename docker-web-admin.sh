#!/bin/bash

echo "🚀 Запуск Web Admin в Docker..."

# Проверяем, что Docker запущен
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker не запущен. Запустите Docker и попробуйте снова."
    exit 1
fi

# Останавливаем существующий контейнер если есть
echo "🛑 Останавливаем существующий контейнер..."
docker stop article-bot-web-admin 2>/dev/null || true
docker rm article-bot-web-admin 2>/dev/null || true

# Собираем и запускаем web admin
echo "🔨 Собираем Docker образ..."
docker-compose -f docker-compose.web-admin.yml build

echo "🚀 Запускаем web admin..."
docker-compose -f docker-compose.web-admin.yml up -d

# Ждем запуска
echo "⏳ Ждем запуска сервиса..."
sleep 5

# Проверяем статус
if docker ps | grep -q article-bot-web-admin; then
    echo "✅ Web Admin успешно запущен!"
    echo "🌐 Админка доступна по адресу: http://localhost:8003"
    echo "🔑 Тестовые учетные данные:"
    echo "   Логин: admin"
    echo "   Пароль: admin123"
    echo ""
    echo "📊 Статус контейнера:"
    docker ps | grep article-bot-web-admin
    echo ""
    echo "📝 Логи:"
    echo "   docker logs article-bot-web-admin"
    echo ""
    echo "🛑 Остановить:"
    echo "   docker-compose -f docker-compose.web-admin.yml down"
else
    echo "❌ Ошибка запуска web admin"
    echo "📝 Логи:"
    docker logs article-bot-web-admin
    exit 1
fi
