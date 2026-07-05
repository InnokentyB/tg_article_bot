#!/usr/bin/env python3
"""
Простой тест API без pytest
"""
import asyncio
import httpx
import json

API_URL = 'https://tg-article-bot-api-production-12d6.up.railway.app'

async def test_api():
    """Простой тест API"""
    print("🧪 Тестирование API...")
    
    async with httpx.AsyncClient() as client:
        # Тест 1: Корневой эндпоинт
        print("\n1️⃣ Тест корневого эндпоинта:")
        try:
            response = await client.get(f"{API_URL}/")
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Ответ: {data}")
                print("   ✅ Успешно")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
        
        # Тест 2: Health check
        print("\n2️⃣ Тест health check:")
        try:
            response = await client.get(f"{API_URL}/health")
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Ответ: {data}")
                print("   ✅ Успешно")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
        
        # Тест 3: API Health check
        print("\n3️⃣ Тест API health check:")
        try:
            response = await client.get(f"{API_URL}/api/health")
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Ответ: {data}")
                print("   ✅ Успешно")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
        
        # Тест 4: Создание статьи
        print("\n4️⃣ Тест создания статьи:")
        try:
            article_data = {
                "text": "Это тестовая статья о технологиях и искусственном интеллекте. Машинное обучение становится все более популярным.",
                "title": "Тестовая статья о технологиях",
                "source": "test"
            }
            response = await client.post(f"{API_URL}/articles", json=article_data)
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Ответ: {data}")
                print("   ✅ Успешно")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
        
        # Тест 5: Создание статьи с Habr
        print("\n5️⃣ Тест создания статьи с Habr:")
        try:
            article_data = {
                "text": "Тренды архитектуры ПО — взгляд InfoQ 2025. Пока все вокруг активно прикручивают большие языковые модели, новые эксперименты всё чаще уходят в сторону более компактных и специализированных SLM и агентного ИИ. RAG уже стал почти обязательной надстройкой, чтобы вытянуть качество ответов из LLM, и теперь архитекторы стараются проектировать системы так, чтобы его было проще встроить.",
                "title": "Тренды архитектуры ПО — взгляд InfoQ 2025",
                "source": "https://habr.com/ru/companies/otus/articles/942048/",
                "telegram_user_id": 123456789
            }
            response = await client.post(f"{API_URL}/articles", json=article_data)
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Ответ: {data}")
                print("   ✅ Успешно")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
        
        # Тест 6: Получение списка статей
        print("\n6️⃣ Тест получения списка статей:")
        try:
            response = await client.get(f"{API_URL}/articles")
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Ответ: {data}")
                print("   ✅ Успешно")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
        
        # Тест 7: Статистика
        print("\n7️⃣ Тест статистики:")
        try:
            response = await client.get(f"{API_URL}/statistics")
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Ответ: {data}")
                print("   ✅ Успешно")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
        
        # Тест 8: Несуществующий эндпоинт
        print("\n8️⃣ Тест несуществующего эндпоинта:")
        try:
            response = await client.get(f"{API_URL}/nonexistent")
            print(f"   Статус: {response.status_code}")
            if response.status_code == 404:
                print("   ✅ Правильно возвращает 404")
            else:
                print(f"   ⚠️ Неожиданный статус: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Исключение: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
