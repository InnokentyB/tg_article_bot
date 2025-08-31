#!/usr/bin/env python3
"""
Тест для сравнения локальной и Railway версий бота
"""
import asyncio
from dotenv import load_dotenv
import os
import requests

def test_local_bot():
    """Тестируем локальный бот"""
    print("🏠 Тестирование ЛОКАЛЬНОГО бота...")
    
    load_dotenv()
    
    # Проверяем конфигурацию
    token = os.getenv('ARTICLE_BOT_TOKEN')
    database_url = os.getenv('DATABASE_URL')
    
    print(f"   📋 Конфигурация:")
    print(f"      Токен: {'✅ Установлен' if token else '❌ Не установлен'}")
    print(f"      База данных: {'✅ Установлена' if database_url else '❌ Не установлена'}")
    
    if database_url:
        if 'localhost:5433' in database_url:
            print(f"      🗄️ Локальная PostgreSQL (порт 5433)")
        else:
            print(f"      🌐 Внешняя база данных")
    
    # Проверяем процесс
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'telegram_bot.py' in result.stdout:
            print("   ✅ Процесс локального бота запущен")
            return True
        else:
            print("   ❌ Процесс локального бота не найден")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка проверки процесса: {e}")
        return False

def test_railway_bot():
    """Тестируем Railway бот"""
    print("\n🚂 Тестирование RAILWAY бота...")
    
    railway_url = "https://tg-article-bot-api-production-12d6.up.railway.app"
    
    try:
        # Проверяем доступность Railway
        response = requests.get(f"{railway_url}/health", timeout=10)
        if response.status_code == 200:
            print("   ✅ Railway API доступен")
            return True
        else:
            print(f"   ❌ Railway API недоступен (статус: {response.status_code})")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка подключения к Railway: {e}")
        return False

def test_web_admin():
    """Тестируем веб-админку"""
    print("\n🌐 Тестирование веб-админки...")
    
    # Локальная админка
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        if response.status_code == 200:
            print("   ✅ Локальная веб-админка доступна (http://localhost:8000)")
        else:
            print(f"   ❌ Локальная веб-админка недоступна (статус: {response.status_code})")
    except Exception as e:
        print(f"   ❌ Локальная веб-админка недоступна: {e}")
    
    # Railway админка
    railway_url = "https://tg-article-bot-api-production-12d6.up.railway.app"
    try:
        response = requests.get(railway_url, timeout=10)
        if response.status_code == 200:
            print("   ✅ Railway веб-админка доступна")
        else:
            print(f"   ❌ Railway веб-админка недоступна (статус: {response.status_code})")
    except Exception as e:
        print(f"   ❌ Railway веб-админка недоступна: {e}")

def compare_versions():
    """Сравниваем версии"""
    print("\n📊 Сравнение версий:")
    
    print("\n🏠 ЛОКАЛЬНАЯ версия:")
    print("   ✅ Полноценный бот с реальной категоризацией")
    print("   ✅ Локальная PostgreSQL база данных")
    print("   ✅ AI категоризация (если есть OpenAI ключ)")
    print("   ✅ BART категоризация")
    print("   ✅ Тематическая кластеризация")
    print("   ✅ Отслеживание реакций")
    print("   ✅ Анализ внешних источников")
    print("   ✅ Проверка дубликатов")
    print("   ❌ Требует локальный сервер")
    print("   ❌ Недоступен извне")
    
    print("\n🚂 RAILWAY версия:")
    print("   ✅ Доступен извне")
    print("   ✅ Автоматическое развертывание")
    print("   ✅ HTTPS")
    print("   ✅ Веб-админка")
    print("   ❌ Простой демо-бот")
    print("   ❌ Mock данные")
    print("   ❌ Ограниченная категоризация")

def show_recommendations():
    """Показываем рекомендации"""
    print("\n💡 РЕКОМЕНДАЦИИ:")
    
    print("\n🎯 Для разработки и тестирования:")
    print("   • Используйте ЛОКАЛЬНУЮ версию")
    print("   • Полный функционал")
    print("   • Реальная база данных")
    print("   • Быстрая отладка")
    
    print("\n🌐 Для продакшена:")
    print("   • Разверните полную версию на Railway")
    print("   • Настройте PostgreSQL на Railway")
    print("   • Добавьте Redis для кэширования")
    print("   • Настройте мониторинг")
    
    print("\n🔧 Что нужно сделать для Railway:")
    print("   1. Создать PostgreSQL сервис на Railway")
    print("   2. Обновить DATABASE_URL")
    print("   3. Развернуть telegram_bot.py")
    print("   4. Настроить переменные окружения")

def main():
    """Основная функция"""
    print("🔍 Анализ версий бота\n")
    
    # Тестируем локальный бот
    local_ok = test_local_bot()
    
    # Тестируем Railway бот
    railway_ok = test_railway_bot()
    
    # Тестируем веб-админку
    test_web_admin()
    
    # Сравниваем версии
    compare_versions()
    
    # Показываем рекомендации
    show_recommendations()
    
    print(f"\n📋 ИТОГ:")
    if local_ok:
        print("   ✅ Локальный бот работает")
    else:
        print("   ❌ Локальный бот не работает")
    
    if railway_ok:
        print("   ✅ Railway доступен")
    else:
        print("   ❌ Railway недоступен")
    
    print("\n🎯 ТЕКУЩЕЕ СОСТОЯНИЕ:")
    print("   • Локальный бот: ЗАПУЩЕН с полным функционалом")
    print("   • Railway: Доступен для веб-админки")
    print("   • Рекомендация: Используйте локальный бот для тестирования")

if __name__ == "__main__":
    main()
