# Настройка и запуск Telegram Article Bot

## Требования

- Python 3.8+
- PostgreSQL база данных
- Telegram Bot Token

## Установка

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd telegram_article_bot_export
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Настройте переменные окружения:**
```bash
export DATABASE_URL="postgresql://username:password@host:port/database"
export ARTICLE_BOT_TOKEN="your_telegram_bot_token"
```

4. **Создайте базу данных PostgreSQL:**
```sql
CREATE DATABASE article_bot;
```

## Запуск

### Только Telegram бот
```bash
python simple_bot.py
```

### Полная система (бот + API сервер)
```bash
python main_bot.py
```

### Только API сервер
```bash
python api_server.py
```

## Проверка сборки

Запустите тест сборки для проверки всех компонентов:
```bash
python test_build.py
```

## Структура проекта

- `simple_bot.py` - Минимальная версия бота
- `main_bot.py` - Полная система с API
- `api_server.py` - FastAPI сервер
- `telegram_bot.py` - Основная логика бота
- `database.py` - Управление базой данных
- `text_extractor.py` - Извлечение текста из URL
- `article_categorizer.py` - Система категоризации
- `config.py` - Конфигурация

## API Endpoints

После запуска API сервера доступны:
- `http://localhost:5000/` - Веб-интерфейс
- `http://localhost:5000/api/articles` - Список статей
- `http://localhost:5000/api/health` - Статус системы

## Решение проблем

### Ошибка подключения к базе данных
Убедитесь, что:
- PostgreSQL запущен
- DATABASE_URL корректный
- База данных существует

### Ошибка Telegram Bot Token
Убедитесь, что:
- Токен получен от @BotFather
- Переменная ARTICLE_BOT_TOKEN установлена

### Ошибки импорта
Запустите:
```bash
pip install -r requirements.txt
python test_build.py
```
