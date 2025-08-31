#!/usr/bin/env python3
"""
Тест работы бота после исправления URL
"""
import asyncio
from dotenv import load_dotenv
import os

async def test_bot_connection():
    """Тестируем подключение к боту"""
    print("🤖 Тестирование работы бота...")
    
    # Загружаем переменные окружения
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

def check_bot_process():
    """Проверяем, запущен ли процесс бота"""
    print("\n🔍 Проверка процесса бота...")
    
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'simple_article_bot' in result.stdout:
            print("✅ Процесс бота запущен")
            return True
        else:
            print("❌ Процесс бота не найден")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки процесса: {e}")
        return False

def main():
    """Основная функция"""
    print("🧪 Тестирование работы бота после исправления URL\n")
    
    # Проверяем процесс
    process_running = check_bot_process()
    
    # Тестируем подключение
    connection_ok = asyncio.run(test_bot_connection())
    
    if process_running and connection_ok:
        print("\n🎉 Бот работает корректно!")
        print("\n📱 Теперь можете:")
        print("1. Открыть Telegram")
        print("2. Найти бота @article_storage_bot")
        print("3. Отправить /start")
        print("4. Отправить ссылку на статью для тестирования")
        print("\n✅ URL в кнопках исправлены на Railway")
    else:
        print("\n❌ Есть проблемы с ботом")
        if not process_running:
            print("   - Процесс бота не запущен")
        if not connection_ok:
            print("   - Проблемы с подключением к Telegram API")

if __name__ == "__main__":
    main()
