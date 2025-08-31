#!/usr/bin/env python3
"""
Проверка конфигурации бота
"""
import os
import asyncio
from dotenv import load_dotenv
from config import BotConfig

def check_bot_config():
    """Проверяем конфигурацию бота"""
    print("🤖 Проверка конфигурации бота...")
    
    # Загружаем переменные окружения
    load_dotenv()
    
    # Проверяем переменные
    token = os.getenv('ARTICLE_BOT_TOKEN')
    database_url = os.getenv('DATABASE_URL')
    api_base_url = os.getenv('API_BASE_URL')
    
    print(f"\n📋 Переменные окружения:")
    print(f"   ARTICLE_BOT_TOKEN: {'✅ Установлен' if token else '❌ Не установлен'}")
    print(f"   DATABASE_URL: {'✅ Установлен' if database_url else '❌ Не установлен'}")
    print(f"   API_BASE_URL: {'✅ Установлен' if api_base_url else '❌ Не установлен'}")
    
    if token:
        print(f"   Токен: {token[:10]}...{token[-10:] if len(token) > 20 else ''}")
    
    # Проверяем конфигурацию через BotConfig
    print(f"\n🔧 Конфигурация BotConfig:")
    bot_info = BotConfig.get_bot_info()
    for key, value in bot_info.items():
        status = "✅" if value else "❌"
        print(f"   {key}: {status}")
    
    # Проверяем валидность
    is_valid = BotConfig.validate_article_bot()
    print(f"\n✅ Валидность конфигурации: {'✅ Валидна' if is_valid else '❌ Невалидна'}")
    
    return is_valid

async def test_bot_connection():
    """Тестируем подключение к Telegram API"""
    print("\n🔗 Тестирование подключения к Telegram API...")
    
    token = os.getenv('ARTICLE_BOT_TOKEN')
    if not token:
        print("❌ Токен не установлен")
        return False
    
    try:
        from aiogram import Bot
        
        bot = Bot(token=token)
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        print(f"✅ Подключение успешно!")
        print(f"   Имя бота: {bot_info.first_name}")
        print(f"   Username: @{bot_info.username}")
        print(f"   ID: {bot_info.id}")
        
        # Проверяем webhook
        webhook_info = await bot.get_webhook_info()
        print(f"\n🌐 Webhook информация:")
        print(f"   URL: {webhook_info.url or 'Не установлен'}")
        print(f"   Ожидает обновлений: {webhook_info.pending_update_count}")
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

async def test_api_connection():
    """Тестируем подключение к API"""
    print("\n🌐 Тестирование подключения к API...")
    
    api_url = os.getenv('API_BASE_URL', 'https://tg-article-bot-api-production-12d6.up.railway.app')
    
    try:
        import requests
        
        # Тестируем health endpoint
        health_url = f"{api_url}/api/health"
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ API доступен: {api_url}")
            data = response.json()
            print(f"   Статус: {data.get('status', 'unknown')}")
            print(f"   Сервис: {data.get('service', 'unknown')}")
        else:
            print(f"❌ API недоступен: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения к API: {e}")

def main():
    """Основная функция"""
    print("🔍 Диагностика бота\n")
    
    # Проверяем конфигурацию
    is_valid = check_bot_config()
    
    if not is_valid:
        print("\n❌ Конфигурация невалидна. Проверьте переменные окружения.")
        return
    
    # Тестируем подключения
    asyncio.run(test_bot_connection())
    asyncio.run(test_api_connection())
    
    print("\n📝 Рекомендации:")
    print("1. Убедитесь, что ARTICLE_BOT_TOKEN установлен в .env")
    print("2. Проверьте, что DATABASE_URL указывает на правильную базу данных")
    print("3. Убедитесь, что API_BASE_URL указывает на правильный сервер")
    print("4. Для локального тестирования используйте simple_article_bot.py")
    print("5. Для продакшена используйте telegram_bot.py")

if __name__ == "__main__":
    main()
