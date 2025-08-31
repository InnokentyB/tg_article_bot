#!/usr/bin/env python3
"""
Тест логина в веб-админку
"""
import requests

def test_login():
    """Тестируем логин"""
    base_url = "https://tg-article-bot-api-production-12d6.up.railway.app"
    
    print("🔐 Тестируем логин в веб-админку...")
    
    # Создаем сессию
    session = requests.Session()
    
    # Шаг 1: Получаем страницу входа
    print("\n1. Получаем страницу входа...")
    try:
        response = session.get(f"{base_url}/", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Страница входа загружена")
        else:
            print(f"   ❌ Ошибка: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return
    
    # Шаг 2: Выполняем логин
    print("\n2. Выполняем логин...")
    login_data = {
        "username": "admin",
        "password": "fakehashedpassword"
    }
    
    try:
        response = session.post(f"{base_url}/login", data=login_data, timeout=10, allow_redirects=False)
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            print("   ✅ Логин успешен, получен редирект")
            redirect_url = response.headers.get('Location', '')
            print(f"   Redirect URL: {redirect_url}")
            
            # Шаг 3: Переходим на dashboard
            print("\n3. Переходим на dashboard...")
            response = session.get(f"{base_url}{redirect_url}", timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Dashboard загружен успешно")
                content = response.text[:200] + "..." if len(response.text) > 200 else response.text
                print(f"   Content: {content}")
            else:
                print(f"   ❌ Ошибка загрузки dashboard: {response.text}")
        else:
            print(f"   ❌ Ошибка логина: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    test_login()
