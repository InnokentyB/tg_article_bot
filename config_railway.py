"""
Configuration for Railway integration
"""
import os
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class RailwayConfig:
    """Configuration for Railway deployment"""
    
    # Bot Configuration
    ARTICLE_BOT_TOKEN: Optional[str] = os.getenv('ARTICLE_BOT_TOKEN')
    
    # Railway API Configuration
    RAILWAY_API_URL: Optional[str] = os.getenv('RAILWAY_API_URL', 'https://tg-article-bot-api-production-12d6.up.railway.app')
    
    # Railway Web Admin Configuration (separate service)
    RAILWAY_WEB_ADMIN_URL: Optional[str] = os.getenv('RAILWAY_WEB_ADMIN_URL', 'https://tg-article-bot-web-admin-production.up.railway.app')
    
    # Database (local fallback)
    DATABASE_URL: Optional[str] = os.getenv('DATABASE_URL')
    
    # Optional AI services
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    
    # Railway specific settings
    USE_RAILWAY_API: bool = os.getenv('USE_RAILWAY_API', 'true').lower() == 'true'
    RAILWAY_API_TIMEOUT: int = int(os.getenv('RAILWAY_API_TIMEOUT', '30'))
    
    # Service detection
    @classmethod
    def detect_railway_service(cls) -> str:
        """Detect which Railway service is currently active"""
        # Check if we're in Railway environment
        if os.getenv('RAILWAY_ENVIRONMENT'):
            # Check which service we're running
            if os.getenv('RAILWAY_SERVICE_NAME') == 'web-admin':
                return 'web-admin'
            elif os.getenv('RAILWAY_SERVICE_NAME') == 'api-server':
                return 'api-server'
            else:
                # Try to detect by checking available endpoints
                return 'unknown'
        return 'local'
    
    @classmethod
    def validate_railway_bot(cls) -> bool:
        """Validate that all required variables for Railway bot are set"""
        required = [cls.ARTICLE_BOT_TOKEN]
        return all(var is not None and var.strip() for var in required)
    
    @classmethod
    def get_railway_info(cls) -> dict:
        """Get Railway configuration info"""
        return {
            'bot_configured': bool(cls.ARTICLE_BOT_TOKEN),
            'railway_api_url': cls.RAILWAY_API_URL,
            'railway_web_admin_url': cls.RAILWAY_WEB_ADMIN_URL,
            'use_railway_api': cls.USE_RAILWAY_API,
            'api_timeout': cls.RAILWAY_API_TIMEOUT,
            'database_configured': bool(cls.DATABASE_URL),
            'ai_configured': bool(cls.OPENAI_API_KEY),
            'current_service': cls.detect_railway_service()
        }
    
    @classmethod
    def get_api_endpoints(cls) -> dict:
        """Get Railway API endpoints"""
        base_url = cls.RAILWAY_API_URL.rstrip('/')
        return {
            'health': f"{base_url}/health",
            'articles': f"{base_url}/api/articles",
            'categories': f"{base_url}/api/categories",
            'stats': f"{base_url}/api/stats",
            'users': f"{base_url}/api/users"
        }
    
    @classmethod
    def get_web_admin_endpoints(cls) -> dict:
        """Get Railway Web Admin endpoints"""
        base_url = cls.RAILWAY_WEB_ADMIN_URL.rstrip('/')
        return {
            'health': f"{base_url}/health",
            'login': f"{base_url}/login",
            'dashboard': f"{base_url}/dashboard",
            'articles': f"{base_url}/articles"
        }
