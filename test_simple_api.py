#!/usr/bin/env python3
"""
Простой тестовый API сервер без тяжелых ML моделей
"""
import asyncio
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import DatabaseManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global components
db_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global db_manager
    logger.info("Initializing simple API server...")
    
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    logger.info("Simple API server initialized")
    yield
    await db_manager.close()
    logger.info("Simple API server shutdown")

# Create FastAPI app
app = FastAPI(
    title="Simple Article Management API",
    description="Simple API for testing without heavy ML models",
    version="1.0.0",
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
    return {"message": "Simple Article Management API", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "simple-article-api"}

@app.get("/api/articles")
async def get_articles():
    """Get articles endpoint"""
    try:
        articles = await db_manager.get_articles(limit=10)
        return {"articles": articles, "count": len(articles)}
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        return {"error": str(e)}

@app.get("/api/stats")
async def get_stats():
    """Get basic stats"""
    try:
        # Get articles count
        async with db_manager.pool.acquire() as conn:
            articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
            users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        
        return {
            "articles_count": articles_count,
            "users_count": users_count,
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")
