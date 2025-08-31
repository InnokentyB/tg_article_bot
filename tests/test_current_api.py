#!/usr/bin/env python3
"""
Простые автотесты для текущего API на Railway
"""
import pytest
import asyncio
import httpx
import os

# Test configuration
API_URL = os.getenv('RAILWAY_API_URL', 'https://tg-article-bot-api-production-12d6.up.railway.app')

class TestCurrentAPI:
    """Тесты для текущего API"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Тест корневого эндпоинта"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "status" in data
            assert data["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Тест health check эндпоинта"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_api_health_endpoint(self):
        """Тест API health check эндпоинта для Railway"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_create_article(self):
        """Тест создания статьи"""
        async with httpx.AsyncClient() as client:
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
    async def test_create_article_habr(self):
        """Тест создания статьи с Habr"""
        async with httpx.AsyncClient() as client:
            article_data = {
                "text": "Тренды архитектуры ПО — взгляд InfoQ 2025. Пока все вокруг активно прикручивают большие языковые модели, новые эксперименты всё чаще уходят в сторону более компактных и специализированных SLM и агентного ИИ.",
                "title": "Тренды архитектуры ПО — взгляд InfoQ 2025",
                "source": "https://habr.com/ru/companies/otus/articles/942048/"
            }
            
            response = await client.post(f"{API_URL}/articles", json=article_data)
            assert response.status_code == 200
            data = response.json()
            
            assert "article_id" in data
            assert "fingerprint" in data
            assert "categories" in data
            assert "status" in data
            assert data["status"] == "created"
    
    @pytest.mark.asyncio
    async def test_create_article_without_text(self):
        """Тест создания статьи без текста"""
        async with httpx.AsyncClient() as client:
            article_data = {
                "title": "Статья без текста",
                "source": "test"
            }
            
            response = await client.post(f"{API_URL}/articles", json=article_data)
            assert response.status_code == 200  # API возвращает ошибку с кодом 200
            data = response.json()
            assert "error" in data
            assert "text is required" in data["error"]
    
    @pytest.mark.asyncio
    async def test_get_articles(self):
        """Тест получения списка статей"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/articles")
            assert response.status_code == 200
            data = response.json()
            assert "articles" in data
            assert "count" in data
            assert isinstance(data["articles"], list)
            assert isinstance(data["count"], int)
    
    @pytest.mark.asyncio
    async def test_statistics_endpoint(self):
        """Тест эндпоинта статистики"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/statistics")
            assert response.status_code == 200
            data = response.json()
            assert "articles_count" in data
            assert "users_count" in data
            assert "database" in data
            assert data["database"] == "enabled"
    
    @pytest.mark.asyncio
    async def test_debug_database(self):
        """Тест эндпоинта отладки базы данных"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/debug/database")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "connected"
            assert "tables" in data
            assert "users" in data["tables"]
            assert "articles" in data["tables"]
