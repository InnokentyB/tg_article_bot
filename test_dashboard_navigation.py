#!/usr/bin/env python3
"""
Тест навигации в dashboard
"""
import requests

def test_dashboard_navigation():
    """Тестируем навигацию в dashboard"""
    base_url = "http://localhost:8000"
    
    print("🧭 Тестируем навигацию в dashboard...")
    
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
            
            # Проверяем наличие ссылок
            admin_checks = [
                ("/users", "Ссылка на пользователей"),
                ("/articles", "Ссылка на статьи"),
                ("/api/statistics", "Ссылка на статистику"),
                ("Управление пользователями", "Кнопка управления пользователями"),
                ("Просмотр статей", "Кнопка просмотра статей"),
                ("Статистика", "Кнопка статистики"),
                ("Последние пользователи", "Секция последних пользователей")
            ]
            
            print("\n🔍 Проверяем навигацию для админа:")
            for check, description in admin_checks:
                if check in content:
                    print(f"   ✅ {description}: найдено")
                else:
                    print(f"   ❌ {description}: не найдено")
            
            # Проверяем статистику
            if "150" in content and "Статей" in content:
                print("✅ Статистика статей отображается")
            else:
                print("❌ Статистика статей не найдена")
                
        else:
            print(f"❌ Ошибка загрузки dashboard: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тестируем как обычный пользователь
    print("\n👤 Тестируем как обычный пользователь...")
    
    # Логинимся как user1
    login_data_user = {
        "username": "user1",
        "password": "userpassword"
    }
    
    try:
        response = session.post(f"{base_url}/login", data=login_data_user, timeout=10, allow_redirects=False)
        if response.status_code != 302:
            print(f"❌ Ошибка логина user1: {response.status_code}")
            return
        print("✅ Логин успешен (user1)")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return
    
    # Тестируем dashboard для обычного пользователя
    try:
        response = session.get(f"{base_url}/dashboard", timeout=10)
        print(f"Dashboard Status (user1): {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Проверяем, что обычный пользователь НЕ видит админские ссылки
            user_checks = [
                ("/articles", "Ссылка на статьи (должна быть)"),
                ("/users", "Ссылка на пользователей (НЕ должна быть)"),
                ("Управление пользователями", "Кнопка управления пользователями (НЕ должна быть)"),
                ("Просмотр статей", "Кнопка просмотра статей (должна быть)")
            ]
            
            print("\n🔍 Проверяем навигацию для обычного пользователя:")
            for check, description in user_checks:
                if check in content:
                    if "НЕ должна быть" in description:
                        print(f"   ❌ {description}: найдено (не должно быть)")
                    else:
                        print(f"   ✅ {description}: найдено")
                else:
                    if "НЕ должна быть" in description:
                        print(f"   ✅ {description}: не найдено (правильно)")
                    else:
                        print(f"   ❌ {description}: не найдено")
                
        else:
            print(f"❌ Ошибка загрузки dashboard: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    test_dashboard_navigation()
