#!/usr/bin/env python3
"""
Тест статуса обоих ботов
"""
import subprocess
import asyncio
from dotenv import load_dotenv
import os

def check_bot_processes():
    """Проверяем процессы ботов"""
    print("🔍 Проверка процессов ботов...")
    
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        output = result.stdout
        
        prod_running = 'telegram_bot.py' in output
        test_running = 'telegram_bot_test.py' in output
        simple_test_running = 'simple_test_bot.py' in output
        
        print(f"   🏭 Продакшен бот: {'✅ Запущен' if prod_running else '❌ Не запущен'}")
        print(f"   🔬 Тестовый бот: {'✅ Запущен' if test_running else '❌ Не запущен'}")
        print(f"   🧪 Упрощенный тестовый: {'✅ Запущен' if simple_test_running else '❌ Не запущен'}")
        
        return {
            'production': prod_running,
            'test': test_running,
            'simple_test': simple_test_running
        }
    except Exception as e:
        print(f"   ❌ Ошибка проверки процессов: {e}")
        return {'production': False, 'test': False, 'simple_test': False}

async def test_bot_connections():
    """Тестируем подключения к ботам"""
    print("\n🔗 Тестирование подключений к ботам...")
    
    load_dotenv()
    
    results = {}
    
    # Тестируем продакшен бота
    prod_token = os.getenv('ARTICLE_BOT_TOKEN')
    if prod_token:
        try:
            from aiogram import Bot
            
            bot = Bot(token=prod_token)
            bot_info = await bot.get_me()
            print(f"   ✅ Продакшен бот: {bot_info.first_name} (@{bot_info.username})")
            results['production'] = True
            
            await bot.session.close()
        except Exception as e:
            print(f"   ❌ Продакшен бот: {e}")
            results['production'] = False
    else:
        print("   ❌ Продакшен токен не найден")
        results['production'] = False
    
    # Тестируем тестового бота
    test_token = os.getenv('ARTICLE_BOT_TEST_TOKEN')
    if test_token:
        try:
            from aiogram import Bot
            
            bot = Bot(token=test_token)
            bot_info = await bot.get_me()
            print(f"   ✅ Тестовый бот: {bot_info.first_name} (@{bot_info.username})")
            results['test'] = True
            
            await bot.session.close()
        except Exception as e:
            print(f"   ❌ Тестовый бот: {e}")
            results['test'] = False
    else:
        print("   ❌ Тестовый токен не найден")
        results['test'] = False
    
    return results

def show_instructions():
    """Показываем инструкции"""
    print("\n📝 ИНСТРУКЦИИ ПО ИСПОЛЬЗОВАНИЮ:")
    
    print("\n🏭 Продакшен бот (@article_storage_bot):")
    print("   1. Запустите: python telegram_bot.py")
    print("   2. Найдите бота: @article_storage_bot")
    print("   3. Отправьте /start")
    print("   4. Отправьте ссылку на статью")
    
    print("\n🔬 Тестовый бот (@article_storage_test_bot):")
    print("   1. Запустите: python run_test_bot.py")
    print("   2. Найдите бота: @article_storage_test_bot")
    print("   3. Отправьте /start")
    print("   4. Отправьте ссылку на статью")
    
    print("\n🧪 Упрощенный тестовый бот (@article_storage_test_bot):")
    print("   1. Запущен: python simple_test_bot.py")
    print("   2. Найдите бота: @article_storage_test_bot")
    print("   3. Отправьте /start")
    print("   4. Отправьте ссылку на статью")

def main():
    """Основная функция"""
    print("🎯 Проверка статуса ботов\n")
    
    # Проверяем процессы
    processes = check_bot_processes()
    
    # Тестируем подключения
    connections = asyncio.run(test_bot_connections())
    
    # Показываем инструкции
    show_instructions()
    
    print(f"\n📋 ИТОГ:")
    if processes.get('production'):
        print("   ✅ Продакшен бот запущен")
    else:
        print("   ❌ Продакшен бот не запущен")
    
    if processes.get('test'):
        print("   ✅ Тестовый бот запущен")
    else:
        print("   ❌ Тестовый бот не запущен")
    
    if processes.get('simple_test'):
        print("   ✅ Упрощенный тестовый бот запущен")
    else:
        print("   ❌ Упрощенный тестовый бот не запущен")
    
    if connections.get('production'):
        print("   ✅ Продакшен бот доступен")
    else:
        print("   ❌ Продакшен бот недоступен")
    
    if connections.get('test'):
        print("   ✅ Тестовый бот доступен")
    else:
        print("   ❌ Тестовый бот недоступен")
    
    print("\n🎯 РЕКОМЕНДАЦИИ:")
    if processes.get('simple_test'):
        print("   • Упрощенный тестовый бот активен - можете тестировать")
        print("   • Найдите @article_storage_test_bot в Telegram")
        print("   • Отправьте /start для начала работы")
    else:
        print("   • Запустите один из ботов для тестирования")
        print("   • Рекомендуется: python simple_test_bot.py")

if __name__ == "__main__":
    main()
