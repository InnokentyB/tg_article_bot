#!/usr/bin/env python3
"""
Тест содержимого страницы статей
"""
import requests
import os

def test_articles_content():
    """Тестируем содержимое страницы статей"""
    base_url = "http://localhost:8000"
    
    print("📰 Тестируем содержимое страницы статей...")
    
    # Создаем сессию
    session = requests.Session()
    
    # Логинимся
    login_data = {
        "username": os.getenv("ADMIN_USERNAME", ""),
        "password": os.getenv("ADMIN_PASSWORD", "")
    }
    
    try:
        response = session.post(f"{base_url}/login", data=login_data, timeout=10, allow_redirects=False)
        if response.status_code != 302:
            print(f"❌ Ошибка логина: {response.status_code}")
            return
        print("✅ Логин успешен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return
    
    # Тестируем страницу статей
    try:
        response = session.get(f"{base_url}/articles?page=1&per_page=20", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Проверяем наличие ключевых элементов
            checks = [
                ("Искусственный интеллект", "Заголовки статей"),
                ("Квантовые вычисления", "Разнообразие статей"),
                ("Технологии", "Категории"),
                ("Наука", "Категории"),
                ("Бизнес", "Категории"),
                ("active", "Статусы статей"),
                ("pending", "Статусы статей"),
                ("Пагинация", "Навигация"),
                ("20", "Количество на странице"),
                ("50", "Опция 50 статей"),
                ("article-card", "Карточки статей"),
                ("btn-outline-primary", "Кнопки действий")
            ]
            
            print("\n🔍 Проверяем содержимое:")
            for check, description in checks:
                if check in content:
                    print(f"   ✅ {description}: найдено '{check}'")
                else:
                    print(f"   ❌ {description}: не найдено '{check}'")
            
            # Подсчитываем статьи
            article_count = content.count("article-card")
            print(f"\n📊 Найдено карточек статей: {article_count}")
            
            # Проверяем пагинацию
            if "Страница 1 из" in content:
                print("✅ Пагинация работает")
            else:
                print("❌ Пагинация не найдена")
                
        else:
            print(f"❌ Ошибка загрузки страницы: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    test_articles_content()
