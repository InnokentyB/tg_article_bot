#!/usr/bin/env python3
"""
Отладка dashboard
"""
import requests

def debug_dashboard():
    """Отладка dashboard"""
    base_url = "http://localhost:8000"
    
    print("🔍 Отладка dashboard...")
    
    # Создаем сессию
    session = requests.Session()
    
    # Логинимся как админ
    login_data = {
        "username": "admin",
        "password": "fakehashedpassword"
    }
    
    try:
        response = session.post(f"{base_url}/login", data=login_data, timeout=10, allow_redirects=False)
        if response.status_code != 302:
            print(f"❌ Ошибка логина: {response.status_code}")
            return
        print("✅ Логин успешен (admin)")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return
    
    # Тестируем dashboard
    try:
        response = session.get(f"{base_url}/dashboard", timeout=10)
        print(f"Dashboard Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Ищем ключевые фразы
            debug_checks = [
                ("is_admin", "Переменная is_admin"),
                ("admin", "Роль admin"),
                ("user.role", "user.role"),
                ("role", "Роль"),
                ("{% if is_admin %}", "Условие is_admin"),
                ("{% if user.role == 'admin' %}", "Условие user.role"),
                ("Пользователи", "Текст 'Пользователи'"),
                ("Управление пользователями", "Текст 'Управление пользователями'"),
                ("Последние пользователи", "Текст 'Последние пользователи'")
            ]
            
            print("\n🔍 Отладочная информация:")
            for check, description in debug_checks:
                if check in content:
                    print(f"   ✅ {description}: найдено '{check}'")
                else:
                    print(f"   ❌ {description}: не найдено '{check}'")
            
            # Ищем конкретные блоки
            if "{% if is_admin %}" in content:
                print("\n📋 Найдены блоки is_admin:")
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "{% if is_admin %}" in line:
                        print(f"   Строка {i+1}: {line.strip()}")
                        # Показать следующие несколько строк
                        for j in range(1, 5):
                            if i+j < len(lines):
                                print(f"   Строка {i+j+1}: {lines[i+j].strip()}")
                
        else:
            print(f"❌ Ошибка загрузки dashboard: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n✅ Отладка завершена!")

if __name__ == "__main__":
    debug_dashboard()
