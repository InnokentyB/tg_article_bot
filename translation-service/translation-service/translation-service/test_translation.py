#!/usr/bin/env python3
"""
Test script for translation service
"""
import asyncio
import httpx
import json

async def test_translation_service():
    """Test translation service endpoints"""
    base_url = "http://localhost:8003"
    
    print("🧪 Testing Translation Service")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        print("\n1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return
        
        # Test providers endpoint
        print("\n2. Testing providers endpoint...")
        try:
            response = await client.get(f"{base_url}/providers")
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"❌ Providers check failed: {e}")
        
        # Test languages endpoint
        print("\n3. Testing languages endpoint...")
        try:
            response = await client.get(f"{base_url}/languages")
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"❌ Languages check failed: {e}")
        
        # Test text translation with Google
        print("\n4. Testing text translation (Google)...")
        try:
            test_data = {
                "text": "Привет, мир! Это тестовое сообщение для проверки перевода.",
                "source_language": "ru",
                "target_language": "en",
                "provider": "google"
            }
            response = await client.post(f"{base_url}/translate", json=test_data)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Original: {result['original_text']}")
                print(f"Translated: {result['translated_text']}")
                print(f"Provider: {result['provider']}")
                print(f"Confidence: {result.get('confidence', 'N/A')}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"❌ Text translation failed: {e}")
        
        # Test article translation
        print("\n5. Testing article translation...")
        try:
            article_data = {
                "title": "Искусственный интеллект в современном мире",
                "content": "Искусственный интеллект (ИИ) становится все более важной частью нашей повседневной жизни. Он помогает нам в работе, учебе и развлечениях. Технологии машинного обучения позволяют компьютерам анализировать большие объемы данных и принимать решения.",
                "summary": "Статья о роли ИИ в современном обществе",
                "source_language": "ru",
                "target_language": "en",
                "provider": "google"
            }
            response = await client.post(f"{base_url}/translate/article", json=article_data)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Original title: {result['original']['title']}")
                print(f"Translated title: {result['translated']['title']}")
                print(f"Provider: {result['provider']}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"❌ Article translation failed: {e}")
    
    print("\n✅ Translation service testing completed!")

if __name__ == "__main__":
    asyncio.run(test_translation_service())
