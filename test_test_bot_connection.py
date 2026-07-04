#!/usr/bin/env python3
"""
Простой тест подключения тестового бота
"""
import asyncio
from dotenv import load_dotenv
import os

async def test_test_bot():
    """Тестируем тестового бота"""
    print("🔬 Тестирование тестового бота...")
    
    load_dotenv()
    
    # Получаем токен
    token = os.getenv('ARTICLE_BOT_TEST_TOKEN')
    if not token:
        print("❌ ARTICLE_BOT_TEST_TOKEN не установлен")
        return False
    print("Токен: установлен")
    
    try:
        from aiogram import Bot
        
        bot = Bot(token=token)
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        print(f"✅ Тестовый бот активен: {bot_info.first_name} (@{bot_info.username})")
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    """Основная функция"""
    print("🧪 Тест подключения тестового бота\n")
    
    success = asyncio.run(test_test_bot())
    
    if success:
        print("\n✅ Тестовый бот доступен!")
        print("Теперь можете:")
        print("1. Запустить: python run_test_bot.py")
        print("2. Найти бота: @article_storage_test_bot")
        print("3. Отправить /start")
    else:
        print("\n❌ Проблемы с тестовым ботом")

if __name__ == "__main__":
    main()
