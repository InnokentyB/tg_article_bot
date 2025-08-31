"""
Configuration management for different bot projects
"""
import os
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class BotConfig:
    """Configuration for article management bot"""
    
    # Article Management Bot
    ARTICLE_BOT_TOKEN: Optional[str] = os.getenv('ARTICLE_BOT_TOKEN')
    ARTICLE_BOT_WEBHOOK_URL: Optional[str] = os.getenv('ARTICLE_BOT_WEBHOOK_URL')
    
    # Database
    DATABASE_URL: Optional[str] = os.getenv('DATABASE_URL')
    
    # Optional AI services
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    
    @classmethod
    def validate_article_bot(cls) -> bool:
        """Validate that all required variables for article bot are set"""
        required = [cls.ARTICLE_BOT_TOKEN, cls.DATABASE_URL]
        return all(var is not None and var.strip() for var in required)
    
    @classmethod
    def get_bot_info(cls) -> dict:
        """Get bot configuration info (without exposing tokens)"""
        return {
            'article_bot_configured': bool(cls.ARTICLE_BOT_TOKEN),
            'webhook_configured': bool(cls.ARTICLE_BOT_WEBHOOK_URL),
            'database_configured': bool(cls.DATABASE_URL),
            'ai_configured': bool(cls.OPENAI_API_KEY)
        }

# Legacy compatibility - переходный период
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Если новая переменная не установлена, используем старую
if not BotConfig.ARTICLE_BOT_TOKEN and TELEGRAM_BOT_TOKEN:
    BotConfig.ARTICLE_BOT_TOKEN = TELEGRAM_BOT_TOKEN
    os.environ['ARTICLE_BOT_TOKEN'] = TELEGRAM_BOT_TOKEN