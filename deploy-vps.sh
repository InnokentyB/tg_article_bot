#!/bin/bash

# Скрипт для развертывания на VPS
# Использование: ./deploy-vps.sh [production|staging]

set -e

ENVIRONMENT=${1:-production}
PROJECT_DIR="/opt/tg_article_bot"
BACKUP_DIR="/opt/backups"

echo "🚀 Развертывание Telegram Article Bot на VPS..."
echo "Окружение: $ENVIRONMENT"

# Проверяем, что мы в правильной директории
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Ошибка: docker-compose.yml не найден"
    exit 1
fi

# Создаем резервную копию базы данных
echo "📦 Создание резервной копии..."
mkdir -p $BACKUP_DIR
if docker-compose exec -T postgres pg_dump -U article_bot article_bot > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql 2>/dev/null; then
    echo "✅ Резервная копия создана"
else
    echo "⚠️  Не удалось создать резервную копию (возможно, БД не запущена)"
fi

# Останавливаем текущие сервисы
echo "🛑 Остановка текущих сервисов..."
docker-compose down

# Получаем последние изменения
echo "📥 Получение последних изменений..."
git pull origin main

# Обновляем образы
echo "🔨 Обновление Docker образов..."
docker-compose pull

# Запускаем сервисы
echo "🚀 Запуск сервисов..."
docker-compose up -d

# Ждем готовности сервисов
echo "⏳ Ожидание готовности сервисов..."
sleep 30

# Проверяем статус
echo "📊 Проверка статуса сервисов..."
docker-compose ps

# Проверяем health check API
echo "🏥 Проверка health check API..."
if curl -f http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "✅ API сервер работает"
else
    echo "❌ API сервер не отвечает"
    docker-compose logs api
    exit 1
fi

# Проверяем подключение к базе данных
echo "🗄️  Проверка подключения к базе данных..."
if docker-compose exec postgres pg_isready -U article_bot > /dev/null 2>&1; then
    echo "✅ База данных работает"
else
    echo "❌ База данных не отвечает"
    exit 1
fi

echo "🎉 Развертывание завершено успешно!"
echo "📊 Статистика:"
echo "   - API: http://localhost:5001"
echo "   - Health: http://localhost:5001/api/health"
echo "   - Статистика: http://localhost:5001/api/stats"

# Очистка старых резервных копий (оставляем последние 10)
echo "🧹 Очистка старых резервных копий..."
ls -t $BACKUP_DIR/backup_*.sql | tail -n +11 | xargs -r rm

echo "✅ Все готово!"
