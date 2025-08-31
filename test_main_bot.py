#!/usr/bin/env python3
"""
Тест основного бота с реальной категоризацией
"""
import asyncio
from dotenv import load_dotenv
import os

def test_main_bot():
    """Тестируем основной бот"""
    print("🤖 Тестирование основного бота с реальной категоризацией...")
    
    # Загружаем переменные окружения
    load_dotenv()
    
    token = os.getenv('ARTICLE_BOT_TOKEN')
    database_url = os.getenv('DATABASE_URL')
    
    print(f"\n📋 Конфигурация:")
    print(f"   Токен: {'✅ Установлен' if token else '❌ Не установлен'}")
    print(f"   База данных: {'✅ Установлена' if database_url else '❌ Не установлена'}")
    
    if token:
        print(f"   Токен: {token[:10]}...{token[-10:]}")
    
    return bool(token and database_url)

async def test_bot_connection():
    """Тестируем подключение к боту"""
    print("\n🔗 Тестирование подключения к Telegram API...")
    
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
        if 'telegram_bot.py' in result.stdout:
            print("✅ Процесс основного бота запущен")
            return True
        else:
            print("❌ Процесс основного бота не найден")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки процесса: {e}")
        return False

def show_categorization_info():
    """Показываем информацию о категоризации"""
    print("\n🏷️ Система категоризации:")
    print("   • Базовая категоризация (rule-based)")
    print("   • AI категоризация (OpenAI)")
    print("   • BART категоризация (transformers)")
    print("   • Тематическая кластеризация")
    print("   • Извлечение ключевых слов")
    print("   • Определение языка")
    print("   • Генерация резюме")

def show_features():
    """Показываем возможности бота"""
    print("\n🎯 Возможности основного бота:")
    print("   • Извлечение текста из URL")
    print("   • Многоуровневая категоризация")
    print("   • Сохранение в PostgreSQL")
    print("   • Отслеживание реакций")
    print("   • Анализ внешних источников")
    print("   • Проверка дубликатов")
    print("   • Генерация отпечатков")
    print("   • Статистика и аналитика")

def main():
    """Основная функция"""
    print("🎉 Тестирование основного бота\n")
    
    # Проверяем конфигурацию
    config_ok = test_main_bot()
    
    # Проверяем процесс
    process_running = check_bot_process()
    
    # Тестируем подключение
    connection_ok = asyncio.run(test_bot_connection())
    
    if config_ok and process_running and connection_ok:
        print("\n🎉 Основной бот готов к работе!")
        
        show_categorization_info()
        show_features()
        
        print("\n📱 Теперь можете:")
        print("1. Открыть Telegram")
        print("2. Найти бота @article_storage_bot")
        print("3. Отправить /start")
        print("4. Отправить ссылку на статью для тестирования")
        
        print("\n📝 Что происходит при обработке статьи:")
        print("   • Извлечение текста из URL")
        print("   • Определение языка")
        print("   • Базовая категоризация")
        print("   • AI категоризация (если доступна)")
        print("   • Сохранение в базу данных")
        print("   • Показ результатов с множественными категориями")
        
        print("\n✅ Все готово к работе с реальной категоризацией!")
    else:
        print("\n❌ Есть проблемы с ботом")
        if not config_ok:
            print("   - Проблемы с конфигурацией")
        if not process_running:
            print("   - Процесс бота не запущен")
        if not connection_ok:
            print("   - Проблемы с подключением к Telegram API")

if __name__ == "__main__":
    main()
