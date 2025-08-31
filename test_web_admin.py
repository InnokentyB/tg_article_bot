#!/usr/bin/env python3
"""
Тест для проверки веб-админки на Railway
"""
import requests
import sys

def test_web_admin():
    """Тестируем веб-админку"""
    base_url = "https://tg-article-bot-api-production-12d6.up.railway.app"
    
    print("🔍 Тестируем веб-админку на Railway...")
    print(f"URL: {base_url}")
    
    # Тест 1: Health check
    print("\n1. Проверяем health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тест 2: Главная страница
    print("\n2. Проверяем главную страницу...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            content = response.text[:200] + "..." if len(response.text) > 200 else response.text
            print(f"   Content: {content}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тест 3: API endpoint (должен быть 404 для веб-админки)
    print("\n3. Проверяем API endpoint...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    test_web_admin()
