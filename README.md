# Telegram Article Management Bot (MVP)

Система управления статьями через Telegram-бот и веб-панель администрирования с автоматической категоризацией, извлечением текстов, обнаружением дубликатов и встроенным семантическим поиском на базе **pgvector**.

---

## 🚀 Возможности MVP

- **📝 Сохранение статей**: Отправка текста (от 50 символов) или URL в Telegram-бот.
- **🔍 Автоматическое извлечение**: Чистый контент из ссылок извлекается с помощью `readability-lxml` и `trafilatura`.
- **🏷️ Категоризация**: Базовая и расширенная автоматическая разметка категорий.
- **🔄 Защита от дубликатов**: SHA-256 fingerprint предотвращает повторное сохранение статей.
- **🧠 Семантический поиск (pgvector)**: Полноценный векторный поиск по темам на стороне базы данных с использованием оператора косинусного сходства (`<=>`).
- **🤖 Критические обзоры**: Генерация Markdown-обзоров и Telegram-черновиков по выбранной теме на основе ИИ (OpenAI) или локального генератора-заглушки.
- **📊 REST API & Web-панель**: Управление статьями, источниками и просмотр статистики.

---

## 🏗️ Каноническая архитектура и точки входа

Все устаревшие и неиспользуемые экспериментальные модули перенесены в директорию `legacy/`.

Основными точками входа в систему являются:
1. **`telegram_bot.py`** — Telegram-бот на фреймворке `aiogram` (v3.x).
2. **`api_server.py`** — REST API сервер на `FastAPI`.
3. **`web_admin.py`** — Панель администрирования.
4. **`database.py`** — Менеджер работы с базой данных PostgreSQL + pgvector.

---

## 🔧 Локальный запуск (Docker-разработка)

Для разработки и тестирования используется локальный стек Docker (Postgres с расширением pgvector, Redis, API-сервер и бот).

### 1. Настройка окружения
Создайте файл `.env` на основе `env.example`:
```bash
# Основные переменные
DATABASE_URL="postgresql://article_bot:article_bot_password@postgres:5432/article_bot"
REDIS_URL="redis://redis:6379/0"
API_KEY="local-dev-key"
JWT_SECRET_KEY="local-jwt"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="admin-password"

# Токен бота (от BotFather)
ARTICLE_BOT_TOKEN="your_telegram_bot_token"

# Настройки ИИ (Опционально)
OPENAI_API_KEY="your_openai_key"
EMBEDDING_PROVIDER="fake" # 'fake' для локальных хэш-векторов или 'openai'
REVIEW_GENERATOR_PROVIDER="fake" # 'fake' или 'openai'
```

### 1.1. Ежедневный дайджест
API умеет собирать ежедневный редакционный дайджест: 5 лучших статей за последние 3 дня, одну статью дня и критический разбор для канала «Читатель Use Case».

Ручной безопасный запуск без публикации:
```bash
curl -X POST "$API_BASE_URL/jobs/daily-digest/run" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true, "period_days": 3, "max_articles": 5}'
```

Автозапуск и публикация управляются отдельно:
```bash
DAILY_DIGEST_ENABLED=false
DAILY_DIGEST_RUN_AT=09:00
DAILY_DIGEST_PUBLISH_ENABLED=false
TELEGRAM_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_channel_id"
```

### 2. Запуск сервисов
Для запуска базы данных, Redis и API-сервера:
```bash
API_KEY=local-dev-key \
JWT_SECRET_KEY=local-jwt \
ADMIN_USERNAME=admin \
ADMIN_PASSWORD=admin-password \
docker compose up -d --build postgres redis api
```

Чтобы запустить и Telegram-бота:
```bash
API_KEY=local-dev-key \
JWT_SECRET_KEY=local-jwt \
ADMIN_USERNAME=admin \
ADMIN_PASSWORD=admin-password \
docker compose --profile bot up -d --build
```

---

## 🧪 Тестирование

Запуск локального набора интеграционных тестов (включая проверку векторного поиска pgvector и RSS-импорта):
```bash
python3 run_tests.py
```

Тестовый набор находится в [tests/test_mvp_api.py](file:///Users/innokentyb/Documents/Product/TGArticles/tests/test_mvp_api.py).

---

## 📂 Структура репозитория

- `api_server.py` — FastAPI сервер.
- `telegram_bot.py` — Telegram-бот.
- `database.py` — Работа с PostgreSQL (схемы, коннекты, pgvector SQL-запросы).
- `embedding_provider.py` — Расчет векторов (Fake / OpenAI).
- `critical_review_generator.py` — Генерация обзоров.
- `article_chunker.py` — Нарезка текстов на чанки.
- `init.sql` — Инициализация схемы БД (таблицы, триггеры, включение расширения vector).
- `legacy/` — Директория с устаревшими модулями и экспериментами.
