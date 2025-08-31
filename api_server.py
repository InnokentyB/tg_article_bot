#!/usr/bin/env python3
"""
API Server для Railway (простая версия)
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
db_manager = None

# Create FastAPI app
app = FastAPI(
    title="Railway API",
    description="API for Railway deployment",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db_manager
    
    logger.info("Starting up API server...")
    
    # Log environment variables
    logger.info(f"PORT: {os.getenv('PORT', 'not set')}")
    logger.info(f"DATABASE_URL: {'set' if os.getenv('DATABASE_URL') else 'not set'}")
    logger.info(f"RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'not set')}")
    
    # Try to initialize database
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Try to create tables if they don't exist
        try:
            async with db_manager.pool.acquire() as conn:
                # Create users table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_user_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(100),
                        first_name VARCHAR(100),
                        last_name VARCHAR(100),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Create articles table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        text TEXT NOT NULL,
                        summary TEXT,
                        fingerprint VARCHAR(64) UNIQUE,
                        source VARCHAR(500),
                        author VARCHAR(200),
                        original_link TEXT,
                        is_translated BOOLEAN DEFAULT FALSE,
                        categories_user TEXT[],
                        categories_auto TEXT[],
                        categories_advanced JSONB,
                        language VARCHAR(10),
                        comments_count INTEGER DEFAULT 0,
                        likes_count INTEGER DEFAULT 0,
                        views_count INTEGER DEFAULT 0,
                        telegram_user_id BIGINT REFERENCES users(telegram_user_id) ON DELETE CASCADE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                logger.info("✅ Database tables created successfully")
                
        except Exception as table_error:
            logger.warning(f"⚠️ Table creation failed: {table_error}")
        
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization failed: {e}")
        db_manager = None

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global db_manager
    
    logger.info("Shutting down API server...")
    
    if db_manager:
        await db_manager.close()
        logger.info("Database connection closed")

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
    logger.info("Root endpoint called")
    return {
        "message": "Railway API is running!", 
        "status": "ok"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check called")
    return {
        "status": "healthy", 
        "service": "railway-api"
    }

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint for Railway"""
    logger.info("API health check called")
    return {
        "status": "healthy", 
        "service": "railway-api"
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint"""
    global db_manager
    
    logger.info("Test endpoint called")
    
    db_status = "connected" if db_manager else "not connected"
    
    return {
        "message": "Test endpoint works!",
        "port": os.getenv("PORT", "not set"),
        "database_url": "set" if os.getenv("DATABASE_URL") else "not set",
        "railway_environment": os.getenv("RAILWAY_ENVIRONMENT", "not set"),
        "database_status": db_status
    }

@app.get("/articles")
async def get_articles(limit: int = 10, offset: int = 0):
    """Get articles"""
    global db_manager
    
    try:
        if db_manager:
            # Use global database manager
            articles = await db_manager.get_articles(limit=limit, offset=offset)
            return {"articles": articles, "count": len(articles)}
        else:
            # Fallback to mock data
            logger.warning("Database not available, using mock data")
            return {
                "articles": [
                    {
                        "id": 1,
                        "title": "Mock Article",
                        "text": "This is a mock article",
                        "categories": ["Technology"],
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                ],
                "count": 1
            }
        
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        return {"error": str(e)}

@app.get("/statistics")
async def get_statistics():
    """Get statistics"""
    try:
        global db_manager
        
        if db_manager:
            try:
                async with db_manager.pool.acquire() as conn:
                    articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
                    users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                
                return {
                    "articles_count": articles_count,
                    "users_count": users_count,
                    "ml_service": "basic",
                    "database": "enabled",
                    "status": "ok"
                }
                
            except Exception as db_error:
                logger.warning(f"Database error, using mock data: {db_error}")
                # Fallback to mock data
                return {
                    "articles_count": 1,
                    "users_count": 1,
                    "ml_service": "basic",
                    "database": "disabled",
                    "status": "ok"
                }
        else:
            # Database not available, use mock data
            logger.warning("Database not available, using mock data")
            return {
                "articles_count": 1,
                "users_count": 1,
                "ml_service": "basic",
                "database": "disabled",
                "status": "ok"
            }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"error": str(e)}

@app.get("/debug/database")
async def debug_database():
    """Debug database connection and tables"""
    global db_manager
    
    try:
        if not db_manager:
            return {
                "status": "error",
                "message": "Database manager not initialized",
                "database_url": "set" if os.getenv("DATABASE_URL") else "not set"
            }
        
        # Test database connection
        async with db_manager.pool.acquire() as conn:
            # Check tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            existing_tables = [row['table_name'] for row in tables]
            
            # Get counts
            users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
            
            return {
                "status": "connected",
                "tables": existing_tables,
                "users_count": users_count,
                "articles_count": articles_count,
                "database_url": "set" if os.getenv("DATABASE_URL") else "not set"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "database_url": "set" if os.getenv("DATABASE_URL") else "not set"
        }

@app.post("/articles")
async def create_article(article_data: dict):
    """Create new article with basic categorization"""
    try:
        text = article_data.get('text', '')
        title = article_data.get('title')
        source = article_data.get('source')
        telegram_user_id = article_data.get('telegram_user_id')
        
        logger.info(f"Creating article: {title}")
        
        if not text:
            return {"error": "Article text is required"}
        
        # Basic categorization
        categories = await basic_categorize(text)
        
        # Try to save to database if available
        global db_manager
        
        if db_manager:
            try:
                # Save user if telegram_user_id provided
                if telegram_user_id:
                    await db_manager.save_user(
                        telegram_user_id=telegram_user_id,
                        username=article_data.get('username'),
                        first_name=article_data.get('first_name'),
                        last_name=article_data.get('last_name')
                    )
                
                # Save article
                result = await db_manager.save_article(
                    title=title,
                    text=text,
                    summary=None,
                    source=source,
                    categories_user=categories,
                    telegram_user_id=telegram_user_id
                )
                
                if result is None:
                    # Article already exists
                    article_id = None
                    fingerprint = "duplicate"
                    status = "duplicate"
                else:
                    article_id, fingerprint = result
                    status = "created"
                
            except Exception as db_error:
                logger.warning(f"Database error, using mock data: {db_error}")
                # Fallback to mock data
                article_id = 1
                fingerprint = "mock-fingerprint"
                status = "created"
        else:
            # Database not available, use mock data
            logger.warning("Database not available, using mock data")
            article_id = 1
            fingerprint = "mock-fingerprint"
            status = "created"
        
        response_data = {
            "article_id": article_id,
            "fingerprint": fingerprint,
            "categories": categories,
            "summary": None,
            "status": status,
            "ml_service": "basic"
        }
        
        logger.info(f"Article created: {response_data}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error creating article: {e}")
        return {"error": str(e)}

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
    logger.info(f"Starting Railway API server on port {port}")
    logger.info(f"Environment PORT: {os.getenv('PORT')}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
