#!/usr/bin/env python3
"""
Тест страницы статей на локальном сервере
"""
import requests
import os

def test_local_articles():
    """Тестируем страницу статей локально"""
    base_url = "http://localhost:8000"
    
    print("📰 Тестируем страницу статей локально...")
    
    # Создаем сессию
    session = requests.Session()
    
    # Шаг 1: Логинимся
    print("\n1. Выполняем логин...")
    login_data = {
        "username": os.getenv("ADMIN_USERNAME", ""),
        "password": os.getenv("ADMIN_PASSWORD", "")
    }
    
    try:
        response = session.post(f"{base_url}/login", data=login_data, timeout=10, allow_redirects=False)
        if response.status_code != 302:
            print(f"   ❌ Ошибка логина: {response.status_code}")
            return
        print("   ✅ Логин успешен")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return
    
    # Шаг 2: Тестируем страницу статей (20 на странице)
    print("\n2. Тестируем страницу статей (20 на странице)...")
    try:
        response = session.get(f"{base_url}/articles?page=1&per_page=20", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Страница статей загружена")
            if "Искусственный интеллект" in response.text:
                print("   ✅ Найдены статьи с реалистичными заголовками")
            else:
                print("   ⚠️ Статьи не найдены или заголовки не соответствуют")
        else:
            print(f"   ❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Шаг 3: Тестируем страницу статей (50 на странице)
    print("\n3. Тестируем страницу статей (50 на странице)...")
    try:
        response = session.get(f"{base_url}/articles?page=1&per_page=50", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Страница статей (50) загружена")
        else:
            print(f"   ❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    test_local_articles()
