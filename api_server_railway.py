#!/usr/bin/env python3
"""
API Server для Railway (упрощенная версия без ML сервиса)
"""
import asyncio
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from database import DatabaseManager
from text_extractor import TextExtractor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global components
db_manager = None
text_extractor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global db_manager, text_extractor
    
    logger.info("Initializing API server for Railway...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Initialize text extractor
    text_extractor = TextExtractor()
    await text_extractor.initialize()
    
    logger.info("API server initialized for Railway")
    yield
    
    # Cleanup
    await db_manager.close()
    await text_extractor.close()
    logger.info("API server shutdown")

# Create FastAPI app
app = FastAPI(
    title="Article Management API (Railway)",
    description="API for article processing - Railway version",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    """Root endpoint"""
    return {
        "message": "Article Management API - Railway Version", 
        "status": "running",
        "ml_service": "disabled"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Simple health check without ML service
        return {
            "status": "healthy", 
            "service": "article-api-railway",
            "ml_service": "disabled"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/articles")
async def create_article(article_data: dict):
    """Create new article with basic categorization"""
    try:
        text = article_data.get('text', '')
        title = article_data.get('title')
        source = article_data.get('source')
        
        if not text:
            raise HTTPException(status_code=400, detail="Article text is required")
        
        # Basic categorization without ML service
        categories = await basic_categorize(text)
        
        # Save to database
        result = await db_manager.save_article(
            title=title,
            text=text,
            summary=None,
            source=source,
            categories_user=categories,
            telegram_user_id=article_data.get('telegram_user_id')
        )
        
        # Handle result from save_article
        if result is None:
            # Article already exists
            article_id = None
            fingerprint = "duplicate"
        else:
            article_id, fingerprint = result
        
        response_data = {
            "article_id": article_id,
            "fingerprint": fingerprint,
            "categories": categories,
            "summary": None,
            "status": "created",
            "ml_service": "disabled"
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error creating article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def basic_categorize(text: str) -> list:
    """Basic categorization without ML service"""
    text_lower = text.lower()
    
    categories = []
    
    # Technology (английские и русские слова)
    tech_words = ['tech', 'technology', 'software', 'ai', 'machine learning', 'programming', 
                 'искусственный интеллект', 'ии', 'программирование', 'технология', 'технологии', 
                 'алгоритм', 'алгоритмы', 'машинное обучение', 'нейросеть', 'нейросети']
    if any(word in text_lower for word in tech_words):
        categories.append('Technology')
    
    # Business (английские и русские слова)
    business_words = ['business', 'finance', 'economy', 'market', 'бизнес', 'финансы', 
                     'экономика', 'рынок', 'компания', 'стартап']
    if any(word in text_lower for word in business_words):
        categories.append('Business')
    
    # Health & Science (английские и русские слова)
    health_words = ['health', 'medical', 'science', 'research', 'здоровье', 'медицина', 
                   'наука', 'исследование', 'медицинский', 'научный']
    if any(word in text_lower for word in health_words):
        categories.append('Health & Science')
    
    # Education (английские и русские слова)
    education_words = ['education', 'learning', 'study', 'course', 'образование', 'обучение', 
                      'изучение', 'курс', 'учебный', 'образовательный']
    if any(word in text_lower for word in education_words):
        categories.append('Education')
    
    if not categories:
        categories = ['General']
    
    return categories

@app.get("/articles")
async def get_articles(limit: int = 10, offset: int = 0):
    """Get articles"""
    try:
        articles = await db_manager.get_articles(limit=limit, offset=offset)
        return {"articles": articles, "count": len(articles)}
        
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get statistics"""
    try:
        async with db_manager.pool.acquire() as conn:
            articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
            users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        
        return {
            "articles_count": articles_count,
            "users_count": users_count,
            "ml_service": "disabled",
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)), log_level="info")
