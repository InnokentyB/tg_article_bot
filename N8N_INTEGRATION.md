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
  "url": "https://example.com/article",  // ИЛИ "text" - что-то одно обязательно!
  "text": "Полный текст статьи...",     // ИЛИ "url" - что-то одно обязательно!
  "force_text": false,                  // Пропустить обработку URL (опционально)
  "title": "Заголовок статьи (опционально)",
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
  "processing_method": "url_extraction",
  "url_processed": true,
  "force_text_used": false,
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

**Body (JSON) - Вариант 1 (только URL):**
```json
{
  "url": "{{ $json.article_url }}",
  "language": "{{ $json.language || 'ru' }}"
}
```

**Body (JSON) - Вариант 2 (только текст):**
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

## 🔧 Решение проблем с URL

### 🚨 Если сайт блокирует запросы:

**Решение 1: Использовать force_text**
```json
{
  "text": "Текст статьи, извлеченный в n8n",
  "title": "Заголовок статьи",
  "force_text": true
}
```

**Решение 2: Извлечение текста в n8n**
1. Добавьте HTTP Request node для получения HTML
2. Добавьте HTML Parser node для извлечения текста
3. Отправьте извлеченный текст в API

**Решение 3: Прямой текст**
```json
{
  "text": "Полный текст статьи",
  "title": "Заголовок",
  "source": "https://original-url.com"
}
```

### 📊 Информация в ответе API:
- `processing_method`: "url_extraction" или "direct_text"
- `url_processed`: true/false
- `force_text_used`: true/false

## 📱 Примеры использования

### Создание статьи по URL
```bash
curl -X POST "https://tg-article-bot-api-production-12d6.up.railway.app/n8n/articles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "url": "https://example.com/article",
    "language": "ru"
  }'
```

### Создание статьи по тексту
```bash
curl -X POST "https://tg-article-bot-api-production-12d6.up.railway.app/n8n/articles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "title": "Тестовая статья",
    "text": "Содержимое тестовой статьи...",
    "source": "n8n"
  }'
```

### Использование force_text
```bash
curl -X POST "https://tg-article-bot-api-production-12d6.up.railway.app/n8n/articles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "text": "Текст статьи, извлеченный в n8n",
    "title": "Заголовок статьи",
    "force_text": true
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
