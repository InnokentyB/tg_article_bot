# 🔧 Исправление проблемы с веб-админкой на Railway

## 🚨 Проблема

У вас развернут API сервер на Railway:
- **URL**: https://tg-article-bot-api-production-12d6.up.railway.app/
- **Статус**: ✅ Работает (возвращает `{"message":"Railway API is running!","status":"ok"}`)

Но веб-админка не доступна по этому адресу.

## ✅ Решение

### Вариант 1: Создать отдельный сервис для веб-админки (Рекомендуется)

1. **В Railway Dashboard**:
   - Нажмите "New Service"
   - Выберите "Deploy from GitHub repo"
   - Укажите: `InnokentyB/tg_article_bot`

2. **Настройте переменные**:
   ```bash
   API_BASE_URL=https://tg-article-bot-api-production-12d6.up.railway.app
   JWT_SECRET_KEY=your-super-secret-jwt-key
   PORT=8000
   ```

3. **Измените Dockerfile**:
   - В настройках сервиса: `Dockerfile Path: Dockerfile.web-admin`
   - Start Command: `python web_admin_railway.py`

4. **Разверните**:
   - Railway автоматически развернет веб-админку

### Вариант 2: Обновить существующий сервис

1. **Обновите `railway.json`**:
   ```json
   {
     "deploy": {
       "startCommand": "python web_admin_railway.py",
       "healthcheckPath": "/health"
     }
   }
   ```

2. **Обновите `Dockerfile`**:
   ```dockerfile
   CMD ["python", "web_admin_railway.py"]
   ```

3. **Разверните**:
   ```bash
   railway up
   ```

## 🌐 Результат

После развертывания у вас будет:

- **API Сервер**: https://tg-article-bot-api-production-12d6.up.railway.app/
- **Веб-админка**: https://your-new-service.railway.app/

### Логин в админку:
- **Логин**: `admin`
- **Пароль**: `fakehashedpassword`

## 🔍 Проверка

### API сервер:
```bash
curl https://tg-article-bot-api-production-12d6.up.railway.app/api/health
```

### Веб-админка (после развертывания):
```bash
curl https://your-new-service.railway.app/health
```

## 📱 Telegram Bot

### Обновление webhook:
```bash
curl -X POST "https://api.telegram.org/bot8016496837:AAHw5dv5b5X_Ad4GKBqVqzEH8izdS0aUytY/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-new-service.railway.app/webhook"}'
```

---

**Рекомендация**: Используйте **Вариант 1** - создайте отдельный сервис для веб-админки. Это обеспечит независимость API и веб-интерфейса.
