#!/usr/bin/env python3
"""
Тесты для текущей версии API на Railway
"""
import pytest
import httpx
import os

# Test configuration
API_URL = 'https://tg-article-bot-api-production-12d6.up.railway.app'

@pytest.fixture
async def client():
    """Async client fixture"""
    async with httpx.AsyncClient() as client:
        yield client

class TestCurrentAPI:
    """Тесты текущей версии API"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Тест корневого эндпоинта"""
        response = await client.get(f"{API_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "ok"
        print(f"✅ Root endpoint: {data}")
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Тест health check эндпоинта"""
        response = await client.get(f"{API_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        print(f"✅ Health endpoint: {data}")
    
    @pytest.mark.asyncio
    async def test_api_health_endpoint(self, client):
        """Тест API health check эндпоинта для Railway"""
        response = await client.get(f"{API_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        print(f"✅ API Health endpoint: {data}")
    
    @pytest.mark.asyncio
    async def test_create_article(self, client):
        """Тест создания статьи"""
        article_data = {
            "text": "Это тестовая статья о технологиях и искусственном интеллекте. Машинное обучение становится все более популярным.",
            "title": "Тестовая статья о технологиях",
            "source": "test"
        }
        
        response = await client.post(f"{API_URL}/articles", json=article_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "article_id" in data
        assert "fingerprint" in data
        assert "categories" in data
        assert "status" in data
        assert data["status"] == "created"
        assert "Technology" in data["categories"]
        print(f"✅ Create article: {data}")
    
    @pytest.mark.asyncio
    async def test_create_habr_article(self, client):
        """Тест создания статьи с Habr"""
        article_data = {
            "text": "Тренды архитектуры ПО — взгляд InfoQ 2025. Пока все вокруг активно прикручивают большие языковые модели, новые эксперименты всё чаще уходят в сторону более компактных и специализированных SLM и агентного ИИ. RAG уже стал почти обязательной надстройкой, чтобы вытянуть качество ответов из LLM, и теперь архитекторы стараются проектировать системы так, чтобы его было проще встроить.",
            "title": "Тренды архитектуры ПО — взгляд InfoQ 2025",
            "source": "https://habr.com/ru/companies/otus/articles/942048/",
            "telegram_user_id": 123456789
        }
        
        response = await client.post(f"{API_URL}/articles", json=article_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "article_id" in data
        assert "categories" in data
        assert "status" in data
        assert data["status"] == "created"
        print(f"✅ Create Habr article: {data}")
    
    @pytest.mark.asyncio
    async def test_create_article_without_text(self, client):
        """Тест создания статьи без текста"""
        article_data = {
            "title": "Статья без текста",
            "source": "test"
        }
        
        response = await client.post(f"{API_URL}/articles", json=article_data)
        assert response.status_code == 400
        print(f"✅ Article without text: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_get_articles(self, client):
        """Тест получения списка статей"""
        response = await client.get(f"{API_URL}/articles")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert "count" in data
        assert isinstance(data["articles"], list)
        assert isinstance(data["count"], int)
        print(f"✅ Get articles: {data}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
