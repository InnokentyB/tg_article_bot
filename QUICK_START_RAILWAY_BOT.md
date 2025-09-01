# 🚀 Быстрый старт Railway Bot

## 📋 Требования

- Python 3.11+
- Telegram Bot Token
- Доступ к Railway API

## ⚡ Быстрый запуск

### 1. Установка зависимостей
```bash
pip install -r requirements.railway_bot.txt
```

### 2. Настройка переменных окружения
```bash
export ARTICLE_BOT_TOKEN="your_bot_token_here"
export RAILWAY_API_URL="https://tg-article-bot-api-production-12d6.up.railway.app"
export USE_RAILWAY_API="true"
```

### 3. Тестирование конфигурации
```bash
python test_bot_config.py
```

### 4. Запуск бота
```bash
python run_railway_bot.py
```

## 🔧 Команды бота

- `/start` - Начать работу
- `/help` - Справка
- `/stats` - Статистика Railway API
- `/status` - Статус API
- `/cancel` - Отменить операцию

## 📝 Обработка статей

1. Отправьте ссылку на статью
2. Бот извлечет содержимое
3. Сохранит в Railway API
4. Предложит категории
5. Выберите категории через кнопки

## 🚨 Устранение неполадок

### Бот не запускается
- Проверьте `ARTICLE_BOT_TOKEN`
- Убедитесь в доступности Railway API

### API недоступен
- Проверьте `RAILWAY_API_URL`
- Дождитесь обновления Railway

### Ошибки категорий
- Некоторые эндпоинты могут быть недоступны
- Используйте команду `/status` для проверки

## 📊 Мониторинг

- Логи: `railway_bot.log`
- Статус: `/status`
- Статистика: `/stats`

---

**🎯 Цель: Интеграция Telegram бота с Railway API для надежного хранения статей**
