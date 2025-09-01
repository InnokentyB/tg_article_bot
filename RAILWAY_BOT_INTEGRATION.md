# 🤖 Telegram Bot + Railway API Integration

Этот проект интегрирует Telegram бота для управления статьями с Railway API, обеспечивая надежное хранение данных и масштабируемость.

## 🏗️ Архитектура

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram Bot  │───▶│  Railway API     │───▶│  PostgreSQL DB  │
│   (Local)       │    │  (Railway)       │    │  (Railway)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📁 Структура файлов

- **`config_railway.py`** - Конфигурация для Railway интеграции
- **`railway_api_client.py`** - Клиент для работы с Railway API
- **`telegram_bot_railway.py`** - Основной бот с Railway интеграцией
- **`run_railway_bot.py`** - Скрипт запуска бота
- **`test_railway_integration.py`** - Тесты интеграции
- **`requirements.railway_bot.txt`** - Зависимости для бота

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.railway_bot.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env`:

```env
# Bot Configuration
ARTICLE_BOT_TOKEN=your_telegram_bot_token_here

# Railway API Configuration
RAILWAY_API_URL=https://your-railway-api.up.railway.app
USE_RAILWAY_API=true
RAILWAY_API_TIMEOUT=30

# Optional: Local database fallback
DATABASE_URL=postgresql://user:pass@localhost/db

# Optional: AI services
OPENAI_API_KEY=your_openai_key_here
```

### 3. Тестирование интеграции

```bash
python test_railway_integration.py
```

### 4. Запуск бота

```bash
python run_railway_bot.py
```

## 🔧 Конфигурация

### RailwayConfig

Основной класс конфигурации с настройками:

- `ARTICLE_BOT_TOKEN` - Токен Telegram бота
- `RAILWAY_API_URL` - URL Railway API
- `USE_RAILWAY_API` - Использовать ли Railway API (true/false)
- `RAILWAY_API_TIMEOUT` - Таймаут для API запросов

### API Endpoints

Автоматически генерируемые эндпоинты:

- `/health` - Проверка здоровья API
- `/api/articles` - Управление статьями
- `/api/categories` - Управление категориями
- `/api/stats` - Статистика
- `/api/users` - Управление пользователями

## 📱 Функции бота

### Команды

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/stats` - Показать статистику Railway API
- `/status` - Проверить статус API
- `/cancel` - Отменить текущую операцию

### Обработка статей

1. **Отправка ссылки** - Бот автоматически извлекает содержимое
2. **Сохранение в Railway** - Данные сохраняются в PostgreSQL
3. **Категоризация** - Предлагаются автоматические и доступные категории
4. **Интерактивный выбор** - Пользователь выбирает категории через кнопки

## 🔌 API Client

### RailwayAPIClient

Асинхронный клиент для работы с Railway API:

```python
async with RailwayAPIClient() as client:
    # Создание статьи
    article = await client.create_article(article_data)
    
    # Получение статистики
    stats = await client.get_statistics()
    
    # Проверка здоровья API
    health = await client.health_check()
```

### Основные методы

- `create_article()` - Создание статьи
- `get_article()` - Получение статьи по ID
- `update_article()` - Обновление статьи
- `get_user_articles()` - Получение статей пользователя
- `get_statistics()` - Получение статистики
- `get_categories()` - Получение доступных категорий
- `create_user()` - Создание/обновление пользователя
- `test_connection()` - Тестирование соединения

## 🧪 Тестирование

### Автоматические тесты

```bash
python test_railway_integration.py
```

Тесты проверяют:

- ✅ Соединение с Railway API
- ✅ Health check эндпоинт
- ✅ Создание пользователей
- ✅ Создание статей
- ✅ Получение и обновление данных
- ✅ Статистику и категории

### Ручное тестирование

1. Запустите бота: `python run_railway_bot.py`
2. Отправьте команду `/start`
3. Отправьте ссылку на статью
4. Проверьте обработку и сохранение

## 📊 Мониторинг

### Логи

Бот ведет подробные логи в файл `railway_bot.log`:

```
2024-01-01 12:00:00 - telegram_bot_railway - INFO - Railway bot initialized successfully
2024-01-01 12:00:01 - railway_api_client - INFO - Railway API connection status: {...}
```

### Статус API

Команда `/status` показывает:

- 🟢 Статус соединения
- 🌐 URL API
- ✅ Работоспособность эндпоинтов
- 🕐 Время последней проверки

## 🚨 Обработка ошибок

### Fallback механизмы

- При недоступности Railway API бот показывает соответствующие сообщения
- Автоматические повторные попытки для критических операций
- Детальное логирование всех ошибок

### Типичные ошибки

- **Connection failed** - Проверьте `RAILWAY_API_URL`
- **Authentication failed** - Проверьте токен бота
- **API timeout** - Увеличьте `RAILWAY_API_TIMEOUT`

## 🔄 Развертывание

### Локальное развертывание

```bash
# Установка зависимостей
pip install -r requirements.railway_bot.txt

# Настройка .env файла
cp .env.example .env
# Отредактируйте .env

# Запуск бота
python run_railway_bot.py
```

### Docker развертывание

```dockerfile
FROM python:3.11-alpine

WORKDIR /app
COPY requirements.railway_bot.txt .
RUN pip install -r requirements.railway_bot.txt

COPY . .
CMD ["python", "run_railway_bot.py"]
```

### Railway развертывание

1. Подключите репозиторий к Railway
2. Установите переменные окружения
3. Railway автоматически развернет API

## 📈 Производительность

### Оптимизации

- Асинхронные HTTP запросы
- Connection pooling для HTTP клиента
- Таймауты для предотвращения зависаний
- Ленивая инициализация компонентов

### Мониторинг

- Время ответа API
- Количество успешных/неуспешных запросов
- Статистика использования

## 🔐 Безопасность

### Защита данных

- Токены хранятся в переменных окружения
- HTTPS для всех API запросов
- Валидация входных данных
- Логирование без чувствительной информации

### Ограничения

- Rate limiting для API запросов
- Таймауты для предотвращения DoS
- Валидация пользовательского ввода

## 🤝 Вклад в проект

### Добавление новых функций

1. Создайте новый метод в `RailwayAPIClient`
2. Добавьте обработчик в `RailwayArticleBot`
3. Напишите тесты в `test_railway_integration.py`
4. Обновите документацию

### Отладка

- Включите DEBUG логирование
- Используйте команду `/status` для проверки API
- Проверьте логи Railway API
- Тестируйте отдельные компоненты

## 📚 Дополнительные ресурсы

- [Railway Documentation](https://docs.railway.app/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [aiogram Documentation](https://docs.aiogram.dev/)

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи бота
2. Убедитесь в корректности конфигурации
3. Протестируйте API отдельно
4. Создайте issue с описанием проблемы

---

**🎉 Успешной интеграции с Railway API!**
