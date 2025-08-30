#!/usr/bin/env python3
"""
Полноценный API Server для Railway с базой данных
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
    
    logger.info("Initializing full Railway API server...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Initialize text extractor
    text_extractor = TextExtractor()
    await text_extractor.initialize()
    
    logger.info("Full Railway API server initialized")
    yield
    
    # Cleanup
    await db_manager.close()
    await text_extractor.close()
    logger.info("Full Railway API server shutdown")

# Create FastAPI app
app = FastAPI(
    title="Article Management API (Railway Full)",
    description="Full API for article processing with database - Railway version",
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
        "message": "Article Management API - Railway Full Version", 
        "status": "running",
        "ml_service": "disabled",
        "database": "enabled"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy", 
            "service": "article-api-railway-full",
            "ml_service": "disabled",
            "database": "enabled"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint for Railway"""
    try:
        logger.info("API health check requested")
        response = {
            "status": "healthy", 
            "service": "article-api-railway-full",
            "ml_service": "disabled",
            "database": "enabled"
        }
        logger.info(f"API health check response: {response}")
        return response
    except Exception as e:
        logger.error(f"API health check failed: {e}")
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

@app.get("/articles")
async def get_articles(limit: int = 10, offset: int = 0):
    """Get articles"""
    try:
        articles = await db_manager.get_articles(limit=limit, offset=offset)
        return {"articles": articles, "count": len(articles)}
        
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/articles/{article_id}")
async def get_article(article_id: int):
    """Get specific article by ID"""
    try:
        async with db_manager.pool.acquire() as conn:
            article = await conn.fetchrow(
                "SELECT * FROM articles WHERE id = $1", 
                article_id
            )
            if not article:
                raise HTTPException(status_code=404, detail="Article not found")
            
            return dict(article)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/articles/fingerprint/{fingerprint}")
async def get_article_by_fingerprint(fingerprint: str):
    """Get article by fingerprint"""
    try:
        async with db_manager.pool.acquire() as conn:
            article = await conn.fetchrow(
                "SELECT * FROM articles WHERE fingerprint = $1", 
                fingerprint
            )
            if not article:
                raise HTTPException(status_code=404, detail="Article not found")
            
            return dict(article)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article by fingerprint {fingerprint}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/articles/{article_id}")
async def delete_article(article_id: int):
    """Delete article by ID"""
    try:
        async with db_manager.pool.acquire() as conn:
            # Check if article exists
            article = await conn.fetchrow("SELECT id, title FROM articles WHERE id = $1", article_id)
            if not article:
                raise HTTPException(status_code=404, detail="Article not found")
            
            # Delete the article
            await conn.execute("DELETE FROM articles WHERE id = $1", article_id)
            
            return {
                "message": "Article deleted successfully",
                "deleted_article": {
                    "id": article_id,
                    "title": article['title']
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/articles/{article_id}/counters")
async def update_counters(article_id: int, counters: dict):
    """Update article counters"""
    try:
        async with db_manager.pool.acquire() as conn:
            # Check if article exists
            article = await conn.fetchrow("SELECT id FROM articles WHERE id = $1", article_id)
            if not article:
                raise HTTPException(status_code=404, detail="Article not found")
            
            # Update counters
            await conn.execute("""
                UPDATE articles 
                SET comments_count = $2, likes_count = $3, views_count = $4, updated_at = NOW()
                WHERE id = $1
            """, article_id, counters.get('comments_count', 0), 
                counters.get('likes_count', 0), counters.get('views_count', 0))
            
            return {"message": "Counters updated successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating counters for article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics")
async def get_statistics():
    """Get comprehensive statistics"""
    try:
        async with db_manager.pool.acquire() as conn:
            articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
            users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            
            # Category statistics
            categories_stats = await conn.fetch("""
                SELECT unnest(categories_user) as category, COUNT(*) as count
                FROM articles 
                WHERE categories_user IS NOT NULL
                GROUP BY category 
                ORDER BY count DESC
            """)
            
            # Recent articles
            recent_articles = await conn.fetch("""
                SELECT id, title, created_at 
                FROM articles 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
        
        return {
            "articles_count": articles_count,
            "users_count": users_count,
            "categories_stats": [dict(row) for row in categories_stats],
            "recent_articles": [dict(row) for row in recent_articles],
            "ml_service": "disabled",
            "database": "enabled",
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get basic statistics (alias for /statistics)"""
    return await get_statistics()

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting full Railway API server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
