"""
Railway API Client for bot integration
"""
import asyncio
import logging
import httpx
from typing import Optional, Dict, List, Any
from datetime import datetime

from config_railway import RailwayConfig

logger = logging.getLogger(__name__)

class RailwayAPIClient:
    """Client for interacting with Railway API"""
    
    def __init__(self):
        self.config = RailwayConfig()
        self.base_url = self.config.RAILWAY_API_URL.rstrip('/')
        self.timeout = self.config.RAILWAY_API_TIMEOUT
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                'User-Agent': 'TelegramBot/1.0',
                'Accept': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check if Railway API is healthy"""
        try:
            async with self:
                response = await self.client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def create_article(self, article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new article via Railway API"""
        try:
            async with self:
                response = await self.client.post(
                    f"{self.base_url}/api/articles",
                    json=article_data
                )
                
                if response.status_code == 201:
                    return response.json()
                else:
                    logger.error(f"Failed to create article: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating article: {e}")
            return None
    
    async def get_article(self, article_id: int) -> Optional[Dict[str, Any]]:
        """Get article by ID from Railway API"""
        try:
            async with self:
                response = await self.client.get(f"{self.base_url}/api/articles/{article_id}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get article: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting article: {e}")
            return None
    
    async def update_article(self, article_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update article via Railway API"""
        try:
            async with self:
                response = await self.client.put(
                    f"{self.base_url}/api/articles/{article_id}",
                    json=update_data
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to update article: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error updating article: {e}")
            return None
    
    async def get_user_articles(self, telegram_user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get articles for a specific user from Railway API"""
        try:
            async with self:
                response = await self.client.get(
                    f"{self.base_url}/api/articles",
                    params={
                        'telegram_user_id': telegram_user_id,
                        'limit': limit
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get user articles: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting user articles: {e}")
            return []
    
    async def get_statistics(self) -> Optional[Dict[str, Any]]:
        """Get statistics from Railway API"""
        try:
            async with self:
                response = await self.client.get(f"{self.base_url}/api/stats")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get statistics: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return None
    
    async def get_categories(self) -> List[str]:
        """Get available categories from Railway API"""
        try:
            async with self:
                response = await self.client.get(f"{self.base_url}/api/categories")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get categories: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create or update user via Railway API"""
        try:
            async with self:
                response = await self.client.post(
                    f"{self.base_url}/api/users",
                    json=user_data
                )
                
                if response.status_code in [201, 200]:
                    return response.json()
                else:
                    logger.error(f"Failed to create user: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Railway API and return status"""
        try:
            # Test health endpoint
            health_ok = await self.health_check()
            
            # Test basic API functionality
            categories = await self.get_categories()
            stats = await self.get_statistics()
            
            return {
                'connected': health_ok,
                'health_endpoint': health_ok,
                'categories_endpoint': len(categories) > 0,
                'stats_endpoint': stats is not None,
                'api_url': self.base_url,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                'connected': False,
                'error': str(e),
                'api_url': self.base_url,
                'timestamp': datetime.now().isoformat()
            }
