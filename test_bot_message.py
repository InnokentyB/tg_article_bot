#!/usr/bin/env python3
"""
Тест обработки сообщений ботом
"""
import asyncio
import requests
from dotenv import load_dotenv
import os

def test_bot_message():
    """Тестируем отправку сообщения боту"""
    print("🤖 Тестирование обработки сообщений ботом...")
    
    # Загружаем переменные окружения
    load_dotenv()
    
    token = os.getenv('ARTICLE_BOT_TOKEN')
    if not token:
        print("❌ Токен бота не найден")
        return
    
    # URL для отправки сообщения (для демонстрации)
    bot_username = "article_storage_bot"
    
    print(f"\n📱 Информация о боте:")
    print(f"   Username: @{bot_username}")
    print(f"   Токен: {token[:10]}...{token[-10:]}")
    
    print(f"\n🔗 Ссылка на бота:")
    print(f"   https://t.me/{bot_username}")
    
    print(f"\n📝 Тестовые сообщения для отправки:")
    print(f"   1. /start - Начать работу с ботом")
    print(f"   2. /help - Получить справку")
    print(f"   3. /stats - Посмотреть статистику")
    print(f"   4. https://example.com/article - Тестовая ссылка на статью")
    print(f"   5. Простой текст - Тестовое текстовое сообщение")
    
    print(f"\n⚠️  Важно:")
    print(f"   - Бот должен быть запущен (simple_article_bot.py)")
    print(f"   - Отправляйте сообщения через Telegram")
    print(f"   - Для тестирования используйте @{bot_username}")
    
    return True

async def check_bot_status():
    """Проверяем статус бота"""
    print("\n🔍 Проверка статуса бота...")
    
    load_dotenv()
    token = os.getenv('ARTICLE_BOT_TOKEN')
    
    if not token:
        print("❌ Токен не найден")
        return False
    
    try:
        from aiogram import Bot
        
        bot = Bot(token=token)
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        print(f"✅ Бот активен: {bot_info.first_name} (@{bot_info.username})")
        
        # Проверяем webhook
        webhook_info = await bot.get_webhook_info()
        print(f"🌐 Webhook: {'Установлен' if webhook_info.url else 'Не установлен'}")
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    """Основная функция"""
    print("🧪 Тестирование бота\n")
    
    # Проверяем статус
    asyncio.run(check_bot_status())
    
    # Тестируем сообщения
    test_bot_message()
    
    print(f"\n📋 Следующие шаги:")
    print(f"1. Откройте Telegram")
    print(f"2. Найдите бота @article_storage_bot")
    print(f"3. Отправьте /start")
    print(f"4. Отправьте ссылку на статью для тестирования")
    print(f"5. Проверьте, что бот отвечает")

if __name__ == "__main__":
    main()
