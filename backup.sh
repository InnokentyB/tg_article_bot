#!/bin/bash

# Скрипт для резервного копирования базы данных
# Использование: ./backup.sh [daily|weekly|monthly]

set -e

BACKUP_TYPE=${1:-daily}
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7
RETENTION_WEEKS=4
RETENTION_MONTHS=12

echo "📦 Создание резервной копии базы данных..."
echo "Тип: $BACKUP_TYPE"
echo "Дата: $DATE"

# Создаем директорию для бэкапов
mkdir -p $BACKUP_DIR

# Создаем резервную копию
BACKUP_FILE="$BACKUP_DIR/backup_${BACKUP_TYPE}_${DATE}.sql"

if docker-compose exec -T postgres pg_dump -U article_bot article_bot > $BACKUP_FILE 2>/dev/null; then
    echo "✅ Резервная копия создана: $BACKUP_FILE"
    
    # Сжимаем файл
    gzip $BACKUP_FILE
    echo "✅ Файл сжат: ${BACKUP_FILE}.gz"
    
    # Удаляем старые бэкапы
    echo "🧹 Очистка старых резервных копий..."
    
    case $BACKUP_TYPE in
        daily)
            find $BACKUP_DIR -name "backup_daily_*.sql.gz" -mtime +$RETENTION_DAYS -delete
            ;;
        weekly)
            find $BACKUP_DIR -name "backup_weekly_*.sql.gz" -mtime +$((RETENTION_WEEKS * 7)) -delete
            ;;
        monthly)
            find $BACKUP_DIR -name "backup_monthly_*.sql.gz" -mtime +$((RETENTION_MONTHS * 30)) -delete
            ;;
    esac
    
    echo "✅ Очистка завершена"
    
    # Показываем статистику
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
    echo "📊 Статистика:"
    echo "   - Размер: $BACKUP_SIZE"
    echo "   - Файл: ${BACKUP_FILE}.gz"
    
else
    echo "❌ Ошибка при создании резервной копии"
    exit 1
fi

echo "🎉 Резервное копирование завершено успешно!"
