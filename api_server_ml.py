#!/usr/bin/env python3
"""
API Server с интеграцией ML сервиса
"""
import asyncio
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx

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
ml_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global db_manager, text_extractor, ml_client
    
    logger.info("Initializing API server with ML integration...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Initialize text extractor
    text_extractor = TextExtractor()
    await text_extractor.initialize()
    
    # Initialize ML service client
    ml_service_url = os.getenv('ML_SERVICE_URL', 'http://ml-service:8000')
    ml_client = httpx.AsyncClient(base_url=ml_service_url, timeout=30.0)
    
    logger.info("API server initialized with ML integration")
    yield
    
    # Cleanup
    await db_manager.close()
    await text_extractor.close()
    await ml_client.aclose()
    logger.info("API server shutdown")

# Create FastAPI app
app = FastAPI(
    title="Article Management API with ML",
    description="API for article processing with external ML service",
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
        "message": "Article Management API with ML Integration", 
        "status": "running",
        "ml_service": "integrated"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check ML service health
        ml_health = await ml_client.get("/health")
        ml_status = "healthy" if ml_health.status_code == 200 else "unhealthy"
    except Exception as e:
        logger.warning(f"ML service health check failed: {e}")
        ml_status = "unreachable"
    
    return {
        "status": "healthy", 
        "service": "article-api-ml",
        "ml_service": ml_status
    }

@app.post("/articles")
async def create_article(article_data: dict):
    """Create new article with ML categorization"""
    try:
        text = article_data.get('text', '')
        title = article_data.get('title')
        source = article_data.get('source')
        
        if not text:
            raise HTTPException(status_code=400, detail="Article text is required")
        
        # Get ML categorization
        ml_response = await ml_client.post("/categorize-detailed", json={
            "text": text,
            "title": title,
            "source": source
        })
        
        if ml_response.status_code != 200:
            logger.warning(f"ML service error: {ml_response.text}")
            # Fallback to basic processing
            categories = ["General"]
            summary = None
            ml_details = None
        else:
            ml_result = ml_response.json()
            categories = ml_result.get('final_categorization', {}).get('categories', ["General"])
            summary = ml_result.get('final_categorization', {}).get('summary')
            ml_details = ml_result
        
        # Save to database
        result = await db_manager.save_article(
            title=title,
            text=text,
            summary=summary,
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
            "summary": summary,
            "status": "created"
        }
        
        # Добавляем детали ML анализа если есть
        if ml_details:
            response_data["ml_analysis"] = {
                "processing_methods": ml_details.get('processing_methods', []),
                "basic_categorization": ml_details.get('basic_categorization'),
                "huggingface_categorization": ml_details.get('huggingface_categorization'),
                "openai_categorization": ml_details.get('openai_categorization'),
                "final_categorization": ml_details.get('final_categorization')
            }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error creating article: {e}")
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

@app.get("/articles")
async def get_articles(limit: int = 10, offset: int = 0):
    """Get articles with optional ML analysis"""
    try:
        articles = await db_manager.get_articles(limit=limit, offset=offset)
        
        # Add ML analysis for each article
        for article in articles:
            if article.get('text'):
                try:
                    ml_response = await ml_client.post("/analyze", json={
                        "text": article['text'][:1000],  # Limit for ML processing
                        "title": article.get('title')
                    })
                    if ml_response.status_code == 200:
                        article['ml_analysis'] = ml_response.json()
                except Exception as e:
                    logger.warning(f"ML analysis failed for article {article.get('id')}: {e}")
                    article['ml_analysis'] = None
        
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
            "ml_service": "integrated",
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
