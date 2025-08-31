#!/usr/bin/env python3
"""
Тест для проверки обоих ботов - продакшен и тестового
"""
import asyncio
from dotenv import load_dotenv
import os

def test_bot_configuration():
    """Тестируем конфигурацию ботов"""
    print("🤖 Тестирование конфигурации ботов...")
    
    load_dotenv()
    
    # Проверяем токены
    prod_token = os.getenv('ARTICLE_BOT_TOKEN')
    test_token = os.getenv('ARTICLE_BOT_TEST_TOKEN')
    database_url = os.getenv('DATABASE_URL')
    
    print(f"\n📋 Конфигурация:")
    print(f"   🏭 Продакшен токен: {'✅ Установлен' if prod_token else '❌ Не установлен'}")
    print(f"   🔬 Тестовый токен: {'✅ Установлен' if test_token else '❌ Не установлен'}")
    print(f"   🗄️ База данных: {'✅ Установлена' if database_url else '❌ Не установлена'}")
    
    if prod_token:
        print(f"   🏭 Продакшен: {prod_token[:10]}...{prod_token[-10:]}")
    if test_token:
        print(f"   🔬 Тестовый: {test_token[:10]}...{test_token[-10:]}")
    
    return bool(prod_token and test_token and database_url)

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

def check_bot_processes():
    """Проверяем процессы ботов"""
    print("\n🔍 Проверка процессов ботов...")
    
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        output = result.stdout
        
        prod_running = 'telegram_bot.py' in output
        test_running = 'telegram_bot_test.py' in output
        
        print(f"   🏭 Продакшен бот: {'✅ Запущен' if prod_running else '❌ Не запущен'}")
        print(f"   🔬 Тестовый бот: {'✅ Запущен' if test_running else '❌ Не запущен'}")
        
        return {'production': prod_running, 'test': test_running}
    except Exception as e:
        print(f"   ❌ Ошибка проверки процессов: {e}")
        return {'production': False, 'test': False}

def show_bot_differences():
    """Показываем различия между ботами"""
    print("\n📊 Сравнение ботов:")
    
    print("\n🏭 ПРОДАКШЕН БОТ (@article_storage_bot):")
    print("   ✅ Полноценный функционал")
    print("   ✅ Реальная база данных")
    print("   ✅ AI категоризация")
    print("   ✅ BART категоризация")
    print("   ✅ Тематическая кластеризация")
    print("   ✅ Отслеживание реакций")
    print("   ✅ Анализ внешних источников")
    print("   ✅ Проверка дубликатов")
    print("   🎯 Назначение: Продакшен использование")
    print("   👥 Аудитория: Реальные пользователи")
    
    print("\n🔬 ТЕСТОВЫЙ БОТ (@article_storage_test_bot):")
    print("   ✅ Полноценный функционал")
    print("   ✅ Тестовая база данных")
    print("   ✅ AI категоризация")
    print("   ✅ BART категоризация")
    print("   ✅ Тематическая кластеризация")
    print("   ✅ Расширенная диагностика")
    print("   ✅ Экспериментальные функции")
    print("   ✅ Подробные логи")
    print("   🎯 Назначение: Тестирование и разработка")
    print("   👥 Аудитория: Разработчики и тестировщики")

def show_usage_instructions():
    """Показываем инструкции по использованию"""
    print("\n📝 ИНСТРУКЦИИ ПО ИСПОЛЬЗОВАНИЮ:")
    
    print("\n🏭 Для продакшена:")
    print("   1. Запустите: python telegram_bot.py")
    print("   2. Найдите бота: @article_storage_bot")
    print("   3. Отправьте /start")
    print("   4. Отправьте ссылку на статью")
    
    print("\n🔬 Для тестирования:")
    print("   1. Запустите: python run_test_bot.py")
    print("   2. Найдите бота: @article_storage_test_bot")
    print("   3. Отправьте /start")
    print("   4. Отправьте ссылку на статью")
    
    print("\n🔄 Переключение между ботами:")
    print("   • Остановите текущий бот: Ctrl+C")
    print("   • Запустите нужный бот")
    print("   • Оба бота используют одну базу данных")
    print("   • Тестовый бот помечает статьи как тестовые")

def main():
    """Основная функция"""
    print("🎯 Тестирование обоих ботов\n")
    
    # Тестируем конфигурацию
    config_ok = test_bot_configuration()
    
    # Тестируем подключения
    connections = asyncio.run(test_bot_connections())
    
    # Проверяем процессы
    processes = check_bot_processes()
    
    # Показываем различия
    show_bot_differences()
    
    # Показываем инструкции
    show_usage_instructions()
    
    print(f"\n📋 ИТОГ:")
    if config_ok:
        print("   ✅ Конфигурация корректна")
    else:
        print("   ❌ Проблемы с конфигурацией")
    
    if connections.get('production'):
        print("   ✅ Продакшен бот доступен")
    else:
        print("   ❌ Продакшен бот недоступен")
    
    if connections.get('test'):
        print("   ✅ Тестовый бот доступен")
    else:
        print("   ❌ Тестовый бот недоступен")
    
    if processes.get('production'):
        print("   ✅ Продакшен бот запущен")
    else:
        print("   ❌ Продакшен бот не запущен")
    
    if processes.get('test'):
        print("   ✅ Тестовый бот запущен")
    else:
        print("   ❌ Тестовый бот не запущен")
    
    print("\n🎯 РЕКОМЕНДАЦИИ:")
    if not processes.get('production') and not processes.get('test'):
        print("   • Запустите один из ботов для тестирования")
    elif processes.get('production') and processes.get('test'):
        print("   • Оба бота запущены - выберите нужный")
    elif processes.get('production'):
        print("   • Продакшен бот активен - для тестирования запустите тестовый")
    elif processes.get('test'):
        print("   • Тестовый бот активен - для продакшена запустите продакшен")

if __name__ == "__main__":
    main()
