# 🚀 Развертывание на Railway

## 📋 Обзор

Railway - это платформа для развертывания приложений, которая автоматически предоставляет базы данных, Redis и другие сервисы.

## 🔧 Подготовка к развертыванию

### 1. Установка Railway CLI
```bash
# macOS
brew install railway

# Или через npm
npm install -g @railway/cli
```

### 2. Авторизация в Railway
```bash
railway login
```

### 3. Инициализация проекта
```bash
railway init
```

## 🚀 Развертывание

### 1. Создание нового проекта
```bash
railway new
```

### 2. Подключение к проекту
```bash
railway link
```

### 3. Настройка переменных окружения
```bash
railway variables set DATABASE_URL="postgresql://..."
railway variables set REDIS_URL="redis://..."
railway variables set ARTICLE_BOT_TOKEN="8016496837:AAHw5dv5b5X_Ad4GKBqVqzEH8izdS0aUytY"
railway variables set JWT_SECRET_KEY="your-super-secret-jwt-key"
railway variables set API_KEY="your-api-key-for-external-services"
railway variables set OPENAI_API_KEY="your-openai-api-key"
```

### 4. Развертывание
```bash
railway up
```

## 🌐 Доступ к приложению

### После развертывания Railway предоставит:
- **Основной URL**: `https://your-app-name.railway.app`
- **Веб-админка**: `https://your-app-name.railway.app`
- **API**: `https://your-app-name.railway.app/api`

### Локальное тестирование
```bash
railway run python api_server_railway_full.py
```

## 📊 Мониторинг

### Просмотр логов
```bash
railway logs
```

### Статус сервисов
```bash
railway status
```

### Переменные окружения
```bash
railway variables
```

## 🔧 Конфигурация

### Файлы конфигурации:
- `railway.toml` - основная конфигурация
- `railway.json` - схема развертывания
- `Dockerfile` - контейнеризация
- `requirements.railway.txt` - зависимости

### Переменные окружения:
```env
# Обязательные
DATABASE_URL=postgresql://username:password@host:port/database
REDIS_URL=redis://username:password@host:port
ARTICLE_BOT_TOKEN=your-bot-token
JWT_SECRET_KEY=your-jwt-secret
API_KEY=your-api-key

# Опциональные
OPENAI_API_KEY=your-openai-key
PORT=5000
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 🗄️ База данных

### Автоматическое создание
Railway автоматически создаст PostgreSQL базу данных при первом развертывании.

### Миграции
```bash
# Запуск миграций
railway run python init_railway_database.py
```

### Подключение к базе
```bash
railway connect
```

## 🔄 Обновление

### Автоматическое обновление
При пуше в GitHub Railway автоматически пересоберет и развернет приложение.

### Ручное обновление
```bash
railway up
```

## 🚨 Устранение неполадок

### Проверка статуса
```bash
railway status
railway logs
```

### Перезапуск сервисов
```bash
railway restart
```

### Откат к предыдущей версии
```bash
railway rollback
```

### Проверка переменных
```bash
railway variables
```

## 📱 Интеграция с Telegram Bot

### Обновление webhook (если нужно)
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-app-name.railway.app/webhook"}'
```

### Проверка webhook
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

## 💰 Стоимость

### Railway Pricing:
- **Free Tier**: $5 кредитов в месяц
- **Pro**: $20/месяц
- **Team**: $20/пользователь/месяц

### Рекомендации:
- Используйте Free Tier для тестирования
- Переходите на Pro для production

## 🔐 Безопасность

### Переменные окружения
- Никогда не коммитьте секреты в Git
- Используйте Railway Variables
- Регулярно ротируйте ключи

### SSL/TLS
- Railway автоматически предоставляет HTTPS
- Все соединения зашифрованы

## 📈 Масштабирование

### Автоматическое масштабирование
Railway автоматически масштабирует приложение в зависимости от нагрузки.

### Мониторинг ресурсов
```bash
railway metrics
```

---

**Статус**: ✅ **ГОТОВО К РАЗВЕРТЫВАНИЮ НА RAILWAY!**
