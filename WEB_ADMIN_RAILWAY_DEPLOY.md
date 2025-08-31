# 🌐 Развертывание веб-админки на Railway

## 🚨 Проблема

У вас уже развернут API сервер на Railway по адресу:
- **API**: https://tg-article-bot-api-production-12d6.up.railway.app/

Но веб-админка не развернута. Нужно создать отдельный сервис для веб-админки.

## 🚀 Решение: Создание второго сервиса

### 1. Создание нового сервиса для веб-админки

```bash
# В Railway Dashboard или через CLI
railway new
# Выберите "Deploy from GitHub repo"
# Укажите тот же репозиторий: InnokentyB/tg_article_bot
```

### 2. Настройка переменных для веб-админки

```bash
railway variables set API_BASE_URL="https://tg-article-bot-api-production-12d6.up.railway.app"
railway variables set JWT_SECRET_KEY="your-super-secret-jwt-key"
railway variables set PORT="8000"
```

### 3. Настройка Dockerfile

В новом сервисе измените `Dockerfile` на `Dockerfile.web-admin`:

```bash
# В Railway Dashboard:
# Build Settings -> Dockerfile Path: Dockerfile.web-admin
# Start Command: python web_admin_railway.py
```

### 4. Развертывание

```bash
railway up
```

## 🌐 Результат

После развертывания у вас будет:

- **API Сервер**: https://tg-article-bot-api-production-12d6.up.railway.app/
- **Веб-админка**: https://your-web-admin-service.railway.app/

### Логин в админку:
- **Логин**: `admin`
- **Пароль**: `fakehashedpassword`

## 🔧 Альтернативное решение: Обновление существующего сервиса

Если хотите обновить существующий сервис:

### 1. Обновите `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "python web_admin_railway.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### 2. Обновите `Dockerfile`:

```dockerfile
# Измените последнюю строку на:
CMD ["python", "web_admin_railway.py"]
```

### 3. Разверните:

```bash
railway up
```

## 📱 Интеграция с Telegram Bot

### Обновление webhook для веб-админки:

```bash
curl -X POST "https://api.telegram.org/bot8016496837:AAHw5dv5b5X_Ad4GKBqVqzEH8izdS0aUytY/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-web-admin-service.railway.app/webhook"}'
```

## 🔍 Проверка работы

### API сервер:
```bash
curl https://tg-article-bot-api-production-12d6.up.railway.app/api/health
```

### Веб-админка:
```bash
curl https://your-web-admin-service.railway.app/health
```

## 🚨 Если что-то пошло не так

### Проверка логов:
```bash
railway logs
```

### Перезапуск:
```bash
railway restart
```

### Проверка переменных:
```bash
railway variables
```

---

**Рекомендация**: Создайте отдельный сервис для веб-админки, чтобы API и веб-интерфейс работали независимо.
