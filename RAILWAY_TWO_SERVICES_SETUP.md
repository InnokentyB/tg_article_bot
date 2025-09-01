# 🚀 Настройка двух сервисов на Railway

## 🏗️ Архитектура

У нас есть два отдельных сервиса на Railway:

1. **API Server** - для Telegram бота
2. **Web Admin** - для веб-интерфейса управления

## 📁 Конфигурационные файлы

### API Server
- **`railway.json`** - основная конфигурация Railway
- **`Dockerfile`** - сборка API сервера
- **`api_server.py`** - основной API сервер

### Web Admin
- **`railway.toml`** - конфигурация для web админки
- **`Dockerfile.web-admin`** - сборка web админки
- **`web_admin_railway.py`** - веб-интерфейс

## 🔧 Настройка на Railway

### Шаг 1: Создание API Server

1. **Создайте новый сервис** в Railway Dashboard
2. **Название**: `tg-article-bot-api`
3. **Источник**: GitHub репозиторий
4. **Конфигурация**: Используйте `railway.json`

### Шаг 2: Создание Web Admin

1. **Создайте второй сервис** в Railway Dashboard
2. **Название**: `tg-article-bot-web-admin`
3. **Источник**: Тот же GitHub репозиторий
4. **Конфигурация**: Используйте `railway.toml`

### Шаг 3: Настройка переменных окружения

#### API Server переменные:
```env
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
ARTICLE_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
```

#### Web Admin переменные:
```env
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET_KEY=your_jwt_secret
API_KEY=your_api_key
```

## 🌐 URL сервисов

После настройки у вас будет:

- **API Server**: `https://tg-article-bot-api-production-xxxx.up.railway.app`
- **Web Admin**: `https://tg-article-bot-web-admin-production-xxxx.up.railway.app`

## 🔄 Обновление конфигурации

### Для API Server:
Обновите `config_railway.py`:
```python
RAILWAY_API_URL = "https://your-api-service-url.up.railway.app"
```

### Для Web Admin:
Обновите `config_railway.py`:
```python
RAILWAY_WEB_ADMIN_URL = "https://your-web-admin-url.up.railway.app"
```

## 🧪 Тестирование

### Тест API Server:
```bash
curl https://your-api-service-url.up.railway.app/health
```

Ожидаемый ответ:
```json
{"status":"healthy","service":"api-server"}
```

### Тест Web Admin:
```bash
curl https://your-web-admin-url.up.railway.app/health
```

Ожидаемый ответ:
```json
{"status":"healthy","service":"web-admin"}
```

## 📱 Интеграция с ботом

Бот будет использовать API Server для:
- Сохранения статей
- Получения статистики
- Управления категориями

Web Admin будет доступен для:
- Просмотра статей
- Управления пользователями
- Аналитики

## 🚨 Важные моменты

1. **Два сервиса = две базы данных** (если не настроить общую)
2. **Разные порты** для каждого сервиса
3. **Отдельные health checks** для каждого сервиса
4. **Разные переменные окружения** для каждого сервиса

## 🔍 Мониторинг

### API Server:
- Health check: `/health`
- Статистика: `/api/stats`
- Статьи: `/api/articles`

### Web Admin:
- Health check: `/health`
- Логин: `/login`
- Дашборд: `/dashboard`

## 📊 Текущий статус

- ✅ **Web Admin**: Работает (показывает страницу входа)
- ⏳ **API Server**: Ожидает настройки в Railway Dashboard

---

**🎯 Цель: Настроить два отдельных сервиса для API и Web Admin на Railway**
