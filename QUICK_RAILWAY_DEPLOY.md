# ⚡ Быстрое развертывание на Railway

## 🚀 Быстрый старт (5 минут)

### 1. Авторизация
```bash
railway login
```

### 2. Создание проекта
```bash
railway new
# Выберите "Deploy from GitHub repo"
# Укажите ваш репозиторий: InnokentyB/tg_article_bot
```

### 3. Настройка переменных
```bash
railway variables set ARTICLE_BOT_TOKEN="8016496837:AAHw5dv5b5X_Ad4GKBqVqzEH8izdS0aUytY"
railway variables set JWT_SECRET_KEY="your-super-secret-jwt-key-change-in-production"
railway variables set API_KEY="your-api-key-for-external-services"
```

### 4. Развертывание
```bash
railway up
```

## 🌐 Доступ к приложению

После развертывания Railway предоставит URL вида:
- **Веб-админка**: `https://your-app-name.railway.app`
- **API**: `https://your-app-name.railway.app/api`

### Логин в админку:
- **Логин**: `admin`
- **Пароль**: `fakehashedpassword`

## 📱 Telegram Bot

### Обновление webhook для production:
```bash
curl -X POST "https://api.telegram.org/bot8016496837:AAHw5dv5b5X_Ad4GKBqVqzEH8izdS0aUytY/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-app-name.railway.app/webhook"}'
```

## 🔧 Мониторинг

### Логи
```bash
railway logs
```

### Статус
```bash
railway status
```

### Переменные
```bash
railway variables
```

## 🚨 Если что-то пошло не так

### Перезапуск
```bash
railway restart
```

### Откат
```bash
railway rollback
```

### Полные логи
```bash
railway logs --follow
```

---

**Время развертывания**: ~5 минут
**Статус**: ✅ **ГОТОВО К ПРОДАКШЕНУ!**
