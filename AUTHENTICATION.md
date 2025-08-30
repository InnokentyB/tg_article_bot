# 🔐 Система аутентификации

## Обзор

В проекте реализована двухуровневая система аутентификации:

1. **JWT токены** - для пользователей (администраторов)
2. **API ключи** - для внешних сервисов
3. **Rate limiting** - защита от DDoS атак

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения
```bash
# Скопируйте пример
cp env.example .env

# Отредактируйте .env файл
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
API_KEY=your-api-key-for-external-services
```

### 3. Запуск сервера
```bash
python api_server.py
```

### 4. Тестирование
```bash
python test_auth.py
```

## 🔑 Типы аутентификации

### JWT Аутентификация (для пользователей)

**Используется для:**
- Доступа к защищенным эндпоинтам
- Управления статьями
- Административных функций

**Как получить токен:**
```bash
curl -X POST "http://localhost:5000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=fakehashedpassword"
```

**Как использовать:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5000/api/articles"
```

### API Key Аутентификация (для внешних сервисов)

**Используется для:**
- Публичных эндпоинтов
- Интеграции с внешними сервисами
- Чтения данных без полного доступа

**Как использовать:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:5000/api/public/articles"
```

## 📋 Защищенные эндпоинты

### Требуют JWT токен:
- `GET /api/articles` - список всех статей
- `GET /api/articles/{id}` - конкретная статья
- `POST /api/articles` - создание статьи
- `PUT /api/articles/{id}/counters` - обновление счетчиков
- `GET /api/auth/me` - информация о пользователе

### Требуют API ключ:
- `GET /api/public/articles` - публичные статьи (ограниченный доступ)

### Без аутентификации:
- `GET /api/health` - проверка здоровья
- `POST /api/auth/login` - вход в систему

## ⚡ Rate Limiting

**Настройки:**
- **Лимит:** 100 запросов в минуту
- **Окно:** 60 секунд
- **При превышении:** HTTP 429

**Настройка:**
```bash
# В .env файле
RATE_LIMIT_WINDOW=60
RATE_LIMIT_MAX_REQUESTS=100
```

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `JWT_SECRET_KEY` | Секретный ключ для JWT | Да |
| `API_KEY` | API ключ для внешних сервисов | Да |
| `RATE_LIMIT_WINDOW` | Окно rate limiting (секунды) | Нет |
| `RATE_LIMIT_MAX_REQUESTS` | Максимум запросов в окне | Нет |

### Пользователи по умолчанию

```python
fake_users_db = {
    "admin": {
        "username": "admin",
        "password": "fakehashedpassword",
        "full_name": "Administrator",
        "email": "admin@example.com"
    }
}
```

## 🛡️ Безопасность

### Рекомендации для продакшена:

1. **Измените секретные ключи:**
```bash
JWT_SECRET_KEY=your-very-long-random-secret-key
API_KEY=your-very-long-random-api-key
```

2. **Используйте HTTPS:**
```bash
uvicorn api_server:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

3. **Настройте базу данных пользователей:**
```python
# Замените fake_users_db на реальную БД
```

4. **Используйте Redis для rate limiting:**
```python
# Замените in-memory storage на Redis
```

5. **Добавьте логирование:**
```python
# Настройте логирование попыток входа
```

## 🧪 Тестирование

### Автоматические тесты:
```bash
python test_auth.py
```

### Ручное тестирование:

1. **Проверка health check:**
```bash
curl http://localhost:5000/api/health
```

2. **Получение JWT токена:**
```bash
curl -X POST "http://localhost:5000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=fakehashedpassword"
```

3. **Доступ к защищенному эндпоинту:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:5000/api/articles"
```

4. **Тест rate limiting:**
```bash
# Быстро отправьте много запросов
for i in {1..150}; do
  curl "http://localhost:5000/api/health"
done
```

## 🚨 Устранение неполадок

### Ошибка 401 Unauthorized
- Проверьте правильность токена
- Убедитесь, что токен не истек
- Проверьте формат заголовка Authorization

### Ошибка 429 Too Many Requests
- Подождите минуту перед следующим запросом
- Увеличьте лимиты в настройках

### Ошибка 500 Internal Server Error
- Проверьте переменные окружения
- Убедитесь, что база данных доступна
- Проверьте логи сервера
