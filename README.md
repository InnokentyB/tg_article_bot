# Telegram Article Management Bot

Система управления статьями через Telegram-бот с автоматической категоризацией, обнаружением дубликатов и REST API.

## Возможности

- 📝 Сохранение статей через текст или URL
- 🔍 Автоматическое извлечение контента из ссылок
- 🏷️ Автоматическая и пользовательская категоризация
- 🔄 Обнаружение дубликатов по fingerprint
- 🌍 Определение языка статей
- 📊 REST API для управления и статистики
- 🎯 FSM-управление для интерактивных функций

## Быстрый старт

### 🐳 Docker (рекомендуется)

#### Полная система (бот + API + база данных)

1. **Настройка переменных окружения:**
```bash
cp env.example .env
# Отредактируйте .env и добавьте ваш Telegram Bot Token
```

2. **Запуск всех сервисов:**
```bash
./docker-start.sh
```

#### Только инфраструктура (для разработки)

```bash
./docker-dev.sh
```

### 🔧 Локальная установка

#### 1. Настройка окружения

```bash
# Основные переменные
export DATABASE_URL="postgresql://user:password@host:port/db"
export ARTICLE_BOT_TOKEN="your_bot_token_here"

# Опционально
export ARTICLE_BOT_WEBHOOK_URL="https://your-domain.com/webhook"
export OPENAI_API_KEY="your_openai_key"  # для расширенной категоризации
```

#### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

#### 3. Запуск

```bash
# Только Telegram бот
python simple_bot.py

# Полная система (бот + API сервер)
python main_bot.py  # бот
python api_server.py  # API сервер
```

## Архитектура

### Компоненты системы

1. **telegram_bot.py** - Основная логика Telegram бота
2. **api_server.py** - FastAPI сервер для REST API
3. **database.py** - Управление PostgreSQL базой данных
4. **text_extractor.py** - Извлечение текста из URL
5. **article_categorizer.py** - Система категоризации
6. **config.py** - Центральная конфигурация

### База данных

```sql
-- Статьи
articles (
    id, title, text, summary, fingerprint,
    source, author, categories_user[], categories_auto[],
    language, telegram_user_id, created_at, updated_at
)

-- Пользователи
users (
    id, telegram_user_id, username, first_name, last_name,
    created_at, updated_at
)
```

## Использование бота

### Команды
- `/start` - Приветствие и инструкции
- `/help` - Подробная справка
- `/stats` - Статистика пользователя

### Отправка статей
1. Отправьте текст статьи (минимум 50 символов)
2. Или отправьте ссылку на статью
3. Бот обработает, проверит дубликаты и предложит добавить категории

### Интерактивное добавление категорий
1. После сохранения статьи появятся кнопки
2. Нажмите "➕ Добавить категории"
3. Введите категории через запятую: `технологии, AI, программирование`
4. Или нажмите "✅ Готово" для завершения

## REST API

API доступен на порту 5000:

- `GET /` - Веб-интерфейс со списком статей
- `GET /api/articles` - Список всех статей
- `GET /api/articles/search?q=query` - Поиск статей
- `POST /api/articles/{id}/increment/{counter}` - Увеличение счетчиков
- `GET /api/health` - Статус системы

## Управление конфигурацией

### Мульти-проектная система

```bash
# Проект управления статьями
export ARTICLE_BOT_TOKEN="bot_token_1"

# Другие проекты
export RSS_BOT_TOKEN="bot_token_2" 
export NEWS_BOT_TOKEN="bot_token_3"
```

### Legacy поддержка

Система автоматически использует `TELEGRAM_BOT_TOKEN` если `ARTICLE_BOT_TOKEN` не установлен.

### Проверка конфигурации

```python
from config import BotConfig

# Проверка готовности
if BotConfig.validate_article_bot():
    print("Бот готов к запуску")

# Статус конфигурации  
print(BotConfig.get_bot_info())
```

## 🐳 Docker команды

### Управление сервисами

```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка всех сервисов
docker-compose down

# Просмотр логов
docker-compose logs -f bot      # Логи бота
docker-compose logs -f api      # Логи API
docker-compose logs -f postgres # Логи базы данных

# Перезапуск сервиса
docker-compose restart bot
docker-compose restart api

# Обновление образов
docker-compose pull
docker-compose up -d --build
```

### Работа с базой данных

```bash
# Подключение к PostgreSQL
docker-compose exec postgres psql -U article_bot -d article_bot

# Резервное копирование
docker-compose exec postgres pg_dump -U article_bot article_bot > backup.sql

# Восстановление из резервной копии
docker-compose exec -T postgres psql -U article_bot -d article_bot < backup.sql
```

### Мониторинг

```bash
# Статус сервисов
docker-compose ps

# Использование ресурсов
docker stats

# Проверка логов
docker-compose logs --tail=100
```

## Решение проблем

### Webhook конфликты
- Система автоматически удаляет webhook при запуске
- Только один экземпляр бота может использовать токен одновременно
- Используйте разные токены для разных проектов

### Обработка дубликатов
- Система создает SHA256 fingerprint для каждой статьи
- При обнаружении дубликата показывается информация о существующей записи
- Дубликаты не сохраняются повторно

### Категоризация
- Автоматическая: на основе ключевых слов (технологии, наука, бизнес и т.д.)
- Пользовательская: интерактивное добавление через FSM
- Обе системы работают независимо

### Docker проблемы

#### Контейнеры не запускаются
```bash
# Проверьте логи
docker-compose logs

# Пересоберите образы
docker-compose build --no-cache
```

#### Проблемы с базой данных
```bash
# Сбросьте данные
docker-compose down -v
docker-compose up -d postgres
```

#### Проблемы с сетью
```bash
# Пересоздайте сеть
docker-compose down
docker network prune
docker-compose up -d
```

## Разработка

### Структура проекта
- `simple_bot.py` - Минимальная версия для тестирования
- `main_bot.py` - Полная система с дополнительными функциями  
- `demo.html` - Веб-интерфейс для демонстрации API

### Отладка
- Логирование на уровне INFO для основных операций
- LSP диагностика для проверки кода
- Автоматические рестарты через Replit workflows

## Лицензия

MIT License - свободное использование и модификация.# Test sync Thu Aug 28 14:37:58 WEST 2025
# CI/CD Test Thu Aug 28 14:46:18 WEST 2025
# Auto-sync test Thu Aug 28 14:52:37 WEST 2025
