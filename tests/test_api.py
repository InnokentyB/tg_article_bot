#!/usr/bin/env python3
"""
Базовые автотесты для API
"""
import pytest
import asyncio
import httpx
import os
from typing import AsyncGenerator

# Test configuration
BASE_URL = os.getenv('TEST_API_URL', 'http://localhost:5000')
API_URL = os.getenv('RAILWAY_API_URL', 'https://tg-article-bot-api-production-12d6.up.railway.app')

@pytest.fixture
async def client():
    """Async client fixture"""
    async with httpx.AsyncClient() as client:
        yield client

class TestHealthEndpoints:
    """Тесты health check эндпоинтов"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Тест корневого эндпоинта"""
        response = await client.get(f"{API_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Тест health check эндпоинта"""
        response = await client.get(f"{API_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_api_health_endpoint(self, client):
        """Тест API health check эндпоинта для Railway"""
        response = await client.get(f"{API_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

class TestArticlesEndpoints:
    """Тесты эндпоинтов статей"""
    
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
    
    @pytest.mark.asyncio
    async def test_create_article_without_text(self, client):
        """Тест создания статьи без текста"""
        article_data = {
            "title": "Статья без текста",
            "source": "test"
        }
        
        response = await client.post(f"{API_URL}/articles", json=article_data)
        assert response.status_code == 400
    
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
    
    @pytest.mark.asyncio
    async def test_get_articles_with_pagination(self, client):
        """Тест получения статей с пагинацией"""
        response = await client.get(f"{API_URL}/articles?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert "count" in data

class TestStatisticsEndpoints:
    """Тесты эндпоинтов статистики"""
    
    @pytest.mark.asyncio
    async def test_statistics_endpoint(self, client):
        """Тест эндпоинта статистики"""
        response = await client.get(f"{API_URL}/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "articles_count" in data
        assert "users_count" in data
        assert "status" in data
        assert data["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_stats_endpoint(self, client):
        """Тест эндпоинта базовой статистики"""
        response = await client.get(f"{API_URL}/stats")
        assert response.status_code == 200
        data = response.json()
        assert "articles_count" in data
        assert "users_count" in data

class TestArticleManagement:
    """Тесты управления статьями"""
    
    @pytest.mark.asyncio
    async def test_get_article_by_id(self, client):
        """Тест получения статьи по ID"""
        # Сначала создаем статью
        article_data = {
            "text": "Статья для тестирования получения по ID",
            "title": "Тест получения по ID",
            "source": "test"
        }
        
        create_response = await client.post(f"{API_URL}/articles", json=article_data)
        assert create_response.status_code == 200
        created_article = create_response.json()
        
        # Получаем статью по ID
        article_id = created_article["article_id"]
        if article_id:  # Если статья была создана (не дубликат)
            response = await client.get(f"{API_URL}/articles/{article_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Тест получения по ID"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_article(self, client):
        """Тест получения несуществующей статьи"""
        response = await client.get(f"{API_URL}/articles/99999")
        assert response.status_code == 404

class TestCategorization:
    """Тесты категоризации"""
    
    @pytest.mark.asyncio
    async def test_technology_categorization(self, client):
        """Тест категоризации технологической статьи"""
        article_data = {
            "text": "Искусственный интеллект и машинное обучение революционизируют мир технологий",
            "title": "AI и ML в технологиях",
            "source": "test"
        }
        
        response = await client.post(f"{API_URL}/articles", json=article_data)
        assert response.status_code == 200
        data = response.json()
        assert "Technology" in data["categories"]
    
    @pytest.mark.asyncio
    async def test_business_categorization(self, client):
        """Тест категоризации бизнес статьи"""
        article_data = {
            "text": "Стартап привлек инвестиции и выходит на рынок",
            "title": "Бизнес новости",
            "source": "test"
        }
        
        response = await client.post(f"{API_URL}/articles", json=article_data)
        assert response.status_code == 200
        data = response.json()
        assert "Business" in data["categories"]
    
    @pytest.mark.asyncio
    async def test_education_categorization(self, client):
        """Тест категоризации образовательной статьи"""
        article_data = {
            "text": "Курс по программированию поможет изучить новые технологии",
            "title": "Образовательные программы",
            "source": "test"
        }
        
        response = await client.post(f"{API_URL}/articles", json=article_data)
        assert response.status_code == 200
        data = response.json()
        assert "Education" in data["categories"]

class TestErrorHandling:
    """Тесты обработки ошибок"""
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, client):
        """Тест обработки неверного JSON"""
        response = await client.post(
            f"{API_URL}/articles", 
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_nonexistent_endpoint(self, client):
        """Тест несуществующего эндпоинта"""
        response = await client.get(f"{API_URL}/nonexistent")
        assert response.status_code == 404

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
