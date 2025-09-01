# 🔗 n8n Integration Guide

## 📋 API Endpoints для n8n

### 🔐 Авторизация
Все защищенные эндпоинты требуют API ключ в заголовке `Authorization`:
```
Authorization: Bearer YOUR_API_KEY
```

### 📝 Создание статьи
**POST** `/n8n/articles`

**Заголовки:**
```
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY
```

**Тело запроса:**
```json
{
  "title": "Заголовок статьи",
  "text": "Полный текст статьи...",
  "summary": "Краткое описание (опционально)",
  "source": "Источник статьи (опционально)",
  "author": "Автор (опционально)",
  "language": "ru (опционально, по умолчанию 'en')"
}
```

**Ответ:**
```json
{
  "success": true,
  "article_id": 123,
  "fingerprint": "abc123...",
  "categories": ["Technology", "Business"],
  "summary": "Краткое описание",
  "status": "created",
  "message": "Article created successfully",
  "ml_service": "basic",
  "source": "n8n",
  "timestamp": "2025-01-01T12:00:00"
}
```

### 📊 Статус API
**GET** `/n8n/status`

**Заголовки:**
```
Authorization: Bearer YOUR_API_KEY
```

**Ответ:**
```json
{
  "status": "healthy",
  "database": "connected",
  "articles_total": 25,
  "users_total": 5,
  "n8n_articles": 10,
  "api_version": "1.0.0",
  "timestamp": "2025-01-01T12:00:00"
}
```

## 🚀 Настройка в n8n

### 1. HTTP Request Node

**URL:** `https://tg-article-bot-api-production-12d6.up.railway.app/n8n/articles`

**Method:** `POST`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY
```

**Body (JSON):**
```json
{
  "title": "{{ $json.title }}",
  "text": "{{ $json.content }}",
  "summary": "{{ $json.summary }}",
  "source": "{{ $json.source_url }}",
  "author": "{{ $json.author }}",
  "language": "{{ $json.language || 'ru' }}"
}
```

### 2. Обработка ответа

**Success Response (200):**
```json
{
  "success": true,
  "article_id": 123,
  "status": "created"
}
```

**Error Response (400/401/403/500):**
```json
{
  "detail": "Error message"
}
```

## 🔧 Настройка переменных окружения

В Railway Dashboard добавьте:

```env
API_KEY=your_secret_api_key_here
```

## 📱 Примеры использования

### Простое создание статьи
```bash
curl -X POST "https://tg-article-bot-api-production-12d6.up.railway.app/n8n/articles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "title": "Тестовая статья",
    "text": "Содержимое тестовой статьи...",
    "source": "https://example.com"
  }'
```

### Проверка статуса
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://tg-article-bot-api-production-12d6.up.railway.app/n8n/status"
```

## 🎯 Особенности n8n интеграции

### ✅ Автоматическое:
- **Категоризация** статей по содержимому
- **Дублирование** проверка по fingerprint
- **Логирование** всех операций
- **Обработка ошибок** с детальными сообщениями

### 🔒 Безопасность:
- **API ключ** авторизация
- **Валидация** входных данных
- **Логирование** всех запросов

### 📊 Мониторинг:
- **Статус API** и базы данных
- **Статистика** по n8n статьям
- **Версионирование** API

## 🚨 Обработка ошибок

### 400 Bad Request
- Отсутствует обязательное поле `text`
- Неверный формат данных

### 401 Unauthorized
- Отсутствует заголовок `Authorization`
- Неверный формат `Bearer` токена

### 403 Forbidden
- Неверный API ключ

### 500 Internal Server Error
- Ошибка базы данных
- Внутренняя ошибка сервера

### 503 Service Unavailable
- База данных недоступна

## 📈 Лучшие практики

1. **Всегда проверяйте** статус ответа
2. **Обрабатывайте ошибки** в n8n workflow
3. **Используйте retry** для временных ошибок
4. **Мониторьте** статус API через `/n8n/status`
5. **Логируйте** все операции в n8n

## 🔍 Отладка

### Проверка логов в Railway:
1. Зайдите в Railway Dashboard
2. Найдите сервис `tg-article-bot-api-production-12d6`
3. Перейдите во вкладку **Deployments**
4. Посмотрите логи последнего деплоя

### Тестирование API:
```bash
# Проверка health
curl https://tg-article-bot-api-production-12d6.up.railway.app/health

# Проверка статуса (с авторизацией)
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://tg-article-bot-api-production-12d6.up.railway.app/n8n/status
```

---

**🎯 Готово к интеграции с n8n!**
