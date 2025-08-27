# Telegram Article Management Bot - API Documentation

## Базовый URL
```
http://localhost:5000
```

## Основные API Endpoints

### 📚 Статьи

#### 1. Получить все статьи
```http
GET /api/articles
```

**Query Parameters:**
- `limit` (int, default: 50) - Количество статей на страницу
- `offset` (int, default: 0) - Смещение для пагинации
- `category` (string, optional) - Фильтр по категории
- `user_id` (int, optional) - Фильтр по пользователю
- `search_text` (string, optional) - Поиск по тексту

**Response:**
```json
{
  "total": 150,
  "articles": [
    {
      "id": 1,
      "title": "Заголовок статьи",
      "summary": "Краткое описание",
      "source": "https://example.com",
      "author": "Автор",
      "original_link": "https://source.com/article",
      "categories_user": ["AI", "Tech"],
      "categories_auto": ["технологии", "ИИ"],
      "language": "ru",
      "comments_count": 15,
      "likes_count": 42,
      "views_count": 1200,
      "telegram_user_id": 123456789,
      "created_at": "2025-08-08T20:30:00Z",
      "updated_at": "2025-08-08T20:35:00Z"
    }
  ]
}
```

#### 2. Получить статью по ID
```http
GET /api/articles/{article_id}
```

**Response:** Объект статьи (как выше)

#### 3. Получить статью по отпечатку
```http
GET /api/articles/fingerprint/{fingerprint}
```

**Response:** Объект статьи

#### 4. Обновить счетчики статьи
```http
PUT /api/articles/{article_id}/counters
```

**Request Body:**
```json
{
  "comments_count": 20,
  "likes_count": 50,
  "views_count": 1500
}
```

### 🔗 Связи с Telegram

#### 5. Получить информацию о связанном сообщении
```http
GET /api/articles/{article_id}/telegram-link
```

**Response:**
```json
{
  "message_id": 999888777,
  "chat_id": -100123456789,
  "title": "Заголовок статьи"
}
```

### 👍 Реакции Telegram

#### 6. Получить реакции статьи
```http
GET /api/articles/{article_id}/reactions
```

**Response:**
```json
{
  "individual_reactions": [
    {
      "reaction_emoji": "👍",
      "telegram_user_id": 123456,
      "created_at": "2025-08-08T20:30:00Z"
    }
  ],
  "reaction_counts": {
    "👍": 5,
    "❤️": 3,
    "🔥": 2
  },
  "total_likes": 10,
  "total_views": 1200,
  "external_stats": {
    "telegram_reactions": {
      "👍": 5,
      "❤️": 3
    },
    "last_reaction_update": "2025-08-08T20:35:00Z"
  }
}
```

### 🌐 Внешние источники

#### 7. Получить статистику внешних источников
```http
GET /api/articles/{article_id}/external-stats
```

**Response:**
```json
{
  "habr": {
    "url": "https://habr.com/ru/articles/123456/",
    "views": 7600,
    "comments": 45,
    "likes": 89,
    "bookmarks": 23,
    "last_updated": "2025-08-08T20:30:00Z"
  },
  "medium": {
    "url": "https://medium.com/@author/article",
    "views": 0,
    "comments": 12,
    "likes": 67,
    "bookmarks": 0,
    "last_updated": "2025-08-08T20:25:00Z"
  }
}
```

#### 8. Начать отслеживание внешнего источника
```http
POST /api/articles/{article_id}/track-external?source_url={url}
```

**Query Parameters:**
- `source_url` (string, required) - URL внешнего источника для отслеживания

**Supported Sources:**
- **Habr.com** - статьи с habr.com
- **Medium.com** - статьи с medium.com  
- **DEV.to** - статьи с dev.to

**Response:**
```json
{
  "message": "Started tracking https://habr.com/article for article 1"
}
```

#### 9. Обновить все внешние источники
```http
PUT /api/external/update-all
```

**Response:**
```json
{
  "message": "Started updating external statistics for all tracked articles"
}
```

### 📊 Статистика

#### 10. Получить общую статистику
```http
GET /api/statistics
```

**Response:**
```json
{
  "total_articles": 150,
  "categories": {
    "технологии": 45,
    "ИИ": 32,
    "программирование": 28
  },
  "languages": {
    "ru": 89,
    "en": 45,
    "unknown": 16
  },
  "top_sources": {
    "habr.com": 67,
    "medium.com": 23,
    "dev.to": 15
  }
}
```

## Коды ответов

- **200 OK** - Успешный запрос
- **404 Not Found** - Ресурс не найден
- **422 Unprocessable Entity** - Ошибки валидации
- **500 Internal Server Error** - Внутренняя ошибка сервера

## Примеры использования

### Получить последние 10 статей
```bash
curl "http://localhost:5000/api/articles?limit=10&offset=0"
```

### Найти статьи по категории
```bash
curl "http://localhost:5000/api/articles?category=AI&limit=20"
```

### Получить реакции конкретной статьи
```bash
curl "http://localhost:5000/api/articles/5/reactions"
```

### Начать отслеживание Habr статьи
```bash
curl -X POST "http://localhost:5000/api/articles/5/track-external?source_url=https://habr.com/ru/articles/123456/"
```

### Обновить счетчики статьи
```bash
curl -X PUT "http://localhost:5000/api/articles/5/counters" \
  -H "Content-Type: application/json" \
  -d '{"likes_count": 100, "views_count": 2500}'
```

## Ошибки

### Пример ошибки 404
```json
{
  "detail": "Article not found"
}
```

### Пример ошибки 422
```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error"
    }
  ]
}
```

## Реализованные фичи

✅ **CRUD операции** для статей
✅ **Поиск и фильтрация** статей  
✅ **Telegram интеграция** - связи с сообщениями и реакции
✅ **Внешние источники** - автоматический сбор статистики
✅ **Статистика и аналитика** - общие метрики системы
✅ **Пагинация** для больших списков
✅ **Валидация данных** через Pydantic модели