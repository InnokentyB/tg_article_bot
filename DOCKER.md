# 🐳 Docker развертывание Telegram Article Bot

## Обзор архитектуры

Проект использует микросервисную архитектуру с Docker Compose:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Telegram  │    │     API     │    │   Nginx     │
│     Bot     │    │   Server    │    │  (Proxy)    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌─────────────┐
                    │ PostgreSQL  │
                    │   Database  │
                    └─────────────┘
                           │
                    ┌─────────────┐
                    │    Redis    │
                    │   (Cache)   │
                    └─────────────┘
```

## Быстрый старт

### 1. Подготовка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd telegram_article_bot_export

# Скопируйте файл с переменными окружения
cp env.example .env
```

### 2. Настройка переменных окружения

Отредактируйте файл `.env`:

```bash
# Обязательные
ARTICLE_BOT_TOKEN=your_telegram_bot_token_here

# Опциональные
OPENAI_API_KEY=your_openai_api_key_here
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### 3. Запуск

```bash
# Полная система
./docker-start.sh

# Или вручную
docker-compose up -d
```

## Режимы работы

### 🚀 Production режим

```bash
# Запуск всех сервисов включая Nginx
docker-compose --profile production up -d
```

**Доступные сервисы:**
- Telegram Bot: работает в фоне
- API Server: http://localhost:5000
- Web Interface: http://localhost:80
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 🔧 Development режим

```bash
# Только инфраструктура
./docker-dev.sh

# Запуск приложения локально
export DATABASE_URL="postgresql://article_bot:article_bot_password@localhost:5432/article_bot"
export REDIS_URL="redis://localhost:6379/0"
export ARTICLE_BOT_TOKEN="your_token"

python simple_bot.py  # или api_server.py
```

## Управление сервисами

### Основные команды

```bash
# Статус сервисов
docker-compose ps

# Логи в реальном времени
docker-compose logs -f bot      # Telegram бот
docker-compose logs -f api      # API сервер
docker-compose logs -f postgres # База данных
docker-compose logs -f redis    # Redis

# Перезапуск сервиса
docker-compose restart bot
docker-compose restart api

# Остановка всех сервисов
docker-compose down

# Остановка с удалением данных
docker-compose down -v
```

### Работа с базой данных

```bash
# Подключение к PostgreSQL
docker-compose exec postgres psql -U article_bot -d article_bot

# Резервное копирование
docker-compose exec postgres pg_dump -U article_bot article_bot > backup.sql

# Восстановление
docker-compose exec -T postgres psql -U article_bot -d article_bot < backup.sql

# Сброс данных
docker-compose down -v
docker-compose up -d postgres
```

### Мониторинг

```bash
# Использование ресурсов
docker stats

# Проверка здоровья сервисов
docker-compose ps

# Последние логи
docker-compose logs --tail=100
```

## Конфигурация

### Переменные окружения

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `ARTICLE_BOT_TOKEN` | Telegram Bot Token | ✅ |
| `DATABASE_URL` | PostgreSQL URL | ✅ (авто) |
| `REDIS_URL` | Redis URL | ✅ (авто) |
| `OPENAI_API_KEY` | OpenAI API Key | ❌ |
| `LOG_LEVEL` | Уровень логирования | ❌ |
| `ENVIRONMENT` | Окружение | ❌ |

### Порты

| Сервис | Порт | Описание |
|--------|------|----------|
| API Server | 5000 | REST API |
| Nginx | 80 | Web Proxy |
| PostgreSQL | 5432 | База данных |
| Redis | 6379 | Кэш |

### Volumes

| Volume | Описание |
|--------|----------|
| `postgres_data` | Данные PostgreSQL |
| `redis_data` | Данные Redis |
| `./logs` | Логи приложения |

## Решение проблем

### Контейнеры не запускаются

```bash
# Проверьте логи
docker-compose logs

# Пересоберите образы
docker-compose build --no-cache

# Проверьте конфигурацию
docker-compose config
```

### Проблемы с базой данных

```bash
# Проверьте статус PostgreSQL
docker-compose exec postgres pg_isready -U article_bot

# Сбросьте данные
docker-compose down -v
docker-compose up -d postgres

# Проверьте инициализацию
docker-compose logs postgres
```

### Проблемы с сетью

```bash
# Пересоздайте сеть
docker-compose down
docker network prune
docker-compose up -d

# Проверьте DNS
docker-compose exec api nslookup postgres
```

### Проблемы с памятью

```bash
# Ограничьте ресурсы в docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## Production развертывание

### Настройка для production

1. **Измените пароли в docker-compose.yml**
2. **Настройте SSL/TLS для Nginx**
3. **Настройте мониторинг**
4. **Настройте резервное копирование**

### Пример production docker-compose.yml

```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}  # Используйте секреты
    volumes:
      - /backup/postgres:/backup  # Резервные копии
      
  api:
    restart: unless-stopped
    deploy:
      replicas: 2  # Масштабирование
```

### Мониторинг и логирование

```bash
# Логирование в файл
docker-compose up -d
docker-compose logs -f > app.log

# Мониторинг с Prometheus/Grafana
# Добавьте соответствующие сервисы в docker-compose.yml
```

## Безопасность

### Рекомендации

1. **Измените пароли по умолчанию**
2. **Используйте секреты для чувствительных данных**
3. **Ограничьте доступ к портам**
4. **Регулярно обновляйте образы**
5. **Настройте firewall**

### Пример с секретами

```bash
# Создайте файл .env.prod
DB_PASSWORD=secure_password_here
BOT_TOKEN=your_bot_token_here

# Используйте в docker-compose.yml
docker-compose --env-file .env.prod up -d
```
