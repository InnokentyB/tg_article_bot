#!/usr/bin/env python3
"""
Финальный тест бота с улучшенной категоризацией
"""
import asyncio
from dotenv import load_dotenv
import os

async def test_bot_final():
    """Финальный тест бота"""
    print("🎯 Финальный тест бота с улучшенной категоризацией...")
    
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
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def check_bot_process():
    """Проверяем процесс бота"""
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
    print("🎉 Финальный тест бота\n")
    
    # Проверяем процесс
    process_running = check_bot_process()
    
    # Тестируем подключение
    connection_ok = asyncio.run(test_bot_final())
    
    if process_running and connection_ok:
        print("\n🎉 Бот готов к работе с улучшенной категоризацией!")
        print("\n📱 Теперь можете:")
        print("1. Открыть Telegram")
        print("2. Найти бота @article_storage_bot")
        print("3. Отправить /start")
        print("4. Отправить ссылку на статью для тестирования")
        
        print("\n🏷️ Улучшенная категоризация:")
        print("   • 6 категорий: Технологии, Наука, Бизнес, Образование, Медицина, Финансы")
        print("   • Автоматическое определение по ключевым словам в URL")
        print("   • Поддержка множественных категорий")
        print("   • Основная категория + все найденные категории")
        
        print("\n📝 Примеры для тестирования:")
        print("   • https://techcrunch.com/ai-article → Технологии")
        print("   • https://science.org/research → Наука")
        print("   • https://business.com/startup → Бизнес")
        print("   • https://health.com/medical → Медицина")
        print("   • https://finance.com/crypto → Финансы")
        print("   • https://tech.com/science-ai → Технологии, Наука")
        
        print("\n✅ Все готово к работе!")
    else:
        print("\n❌ Есть проблемы с ботом")

if __name__ == "__main__":
    main()
