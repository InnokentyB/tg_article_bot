#!/usr/bin/env python3
"""
API Server для Railway (простая версия)
"""
import os
import logging
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
db_manager = None

# Global variables
db_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    global db_manager
    
    # Startup
    logger.info("Starting up API server...")
    
    # Log environment variables
    logger.info(f"PORT: {os.getenv('PORT', 'not set')}")
    logger.info(f"DATABASE_URL: {'set' if os.getenv('DATABASE_URL') else 'not set'}")
    logger.info(f"RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'not set')}")
    logger.info(f"API_KEY: {'set' if os.getenv('API_KEY') else 'not set'}")
    
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
    
    yield
    
    # Shutdown
    logger.info("Shutting down API server...")
    if db_manager:
        await db_manager.close()
        logger.info("Database connection closed")

# Create FastAPI app
app = FastAPI(
    title="Railway API",
    description="API for Railway deployment with n8n integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key from Authorization header"""
    api_key = os.getenv('API_KEY')
    
    if not api_key:
        logger.warning("API_KEY not set, skipping authentication")
        return True
    
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if it's a Bearer token
    if not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=401, 
            detail="Invalid authorization format. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract token
    token = authorization.replace('Bearer ', '')
    
    if token != api_key:
        raise HTTPException(
            status_code=403, 
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return True



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
async def create_article(article_data: dict, auth: bool = Depends(verify_api_key)):
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

@app.post("/n8n/articles")
async def create_article_n8n(article_data: dict, auth: bool = Depends(verify_api_key)):
    """Create new article from n8n with URL or text"""
    try:
        url = article_data.get('url', '')
        text = article_data.get('text', '')
        force_text = article_data.get('force_text', False)
        title = article_data.get('title', 'Untitled Article')
        source = article_data.get('source', 'n8n')
        author = article_data.get('author')
        summary = article_data.get('summary')
        language = article_data.get('language', 'en')

        logger.info(f"Creating article from n8n: {title}")

                # Check if we have either URL or text
        if not url and not text:
            raise HTTPException(
                status_code=400,
                detail="Either 'url' or 'text' is required. Provide one of them."
            )

        # If force_text is enabled, skip URL processing
        if force_text:
            url = None
            logger.info("Force text mode enabled, skipping URL processing")

        # If URL provided, extract text from it
        if url:
            try:
                logger.info(f"Starting URL extraction for: {url}")
                from text_extractor import TextExtractor
                text_extractor = TextExtractor()
                await text_extractor.initialize()

                extracted_data = await text_extractor.extract_from_url(url)
                logger.info(f"Text extraction result: {extracted_data}")

                if not extracted_data or not extracted_data.get('text'):
                    logger.error(f"Failed to extract data from URL: {url}")
                    logger.error(f"Extracted data: {extracted_data}")
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to extract text from URL. Please provide 'text' instead."
                    )

                # Use extracted data if not provided
                if not text:
                    text = extracted_data.get('text', '')
                    logger.info(f"Using extracted text, length: {len(text)}")
                if not title or title == 'Untitled Article':
                    title = extracted_data.get('title', 'Untitled Article')
                    logger.info(f"Using extracted title: {title}")
                if not summary:
                    summary = extracted_data.get('summary', '')
                    logger.info(f"Using extracted summary, length: {len(summary) if summary else 0}")

                # Close text extractor
                await text_extractor.close()
                logger.info("Text extractor closed successfully")

            except Exception as extract_error:
                logger.error(f"Error extracting text from URL: {extract_error}")
                logger.error(f"Error type: {type(extract_error).__name__}")
                logger.error(f"Error details: {str(extract_error)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to extract text from URL: {str(extract_error)}. Try one of these solutions: 1) Send text directly with 'text' field, 2) Use 'force_text': true with pre-extracted text, 3) Extract text in n8n first."
                )

        # Basic categorization - fast synchronous operation
        categories = await basic_categorize(text)

        # Try to save to database if available
        global db_manager

        if db_manager:
            try:
                # Save article
                result = await db_manager.save_article(
                    title=title,
                    text=text,
                    summary=summary,
                    source=source,
                    author=author,
                    language=language,
                    categories_user=categories,
                    telegram_user_id=None  # n8n articles don't have telegram user
                )

                if result is None:
                    # Article already exists
                    article_id = None
                    fingerprint = "duplicate"
                    status = "duplicate"
                    message = "Article already exists (duplicate content)"
                else:
                    article_id, fingerprint = result
                    status = "created"
                    message = "Article created successfully"

            except Exception as db_error:
                logger.error(f"Database error: {db_error}")
                raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        else:
            raise HTTPException(status_code=503, detail="Database not available")

        response_data = {
            "success": True,
            "article_id": article_id,
            "fingerprint": fingerprint,
            "categories": categories,
            "summary": summary,
            "status": status,
            "message": message,
            "ml_service": "basic",
            "source": "n8n",
            "processing_method": "url_extraction" if url else "direct_text",
            "url_processed": bool(url),
            "force_text_used": force_text,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Article created from n8n: {response_data}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating article from n8n: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/n8n/articles/fast")
async def create_article_n8n_fast(article_data: dict, auth: bool = Depends(verify_api_key)):
    """Fast version - only text processing, skip URL extraction"""
    try:
        text = article_data.get('text', '')
        title = article_data.get('title', 'Untitled Article')
        source = article_data.get('source', 'n8n')
        author = article_data.get('author')
        summary = article_data.get('summary')
        language = article_data.get('language', 'en')

        logger.info(f"Fast creating article from n8n: {title}")

        if not text:
            raise HTTPException(
                status_code=400,
                detail="Text is required for fast endpoint"
            )

        # Fast categorization
        categories = await basic_categorize(text)

        # Save to database
        global db_manager

        if db_manager:
            try:
                result = await db_manager.save_article(
                    title=title,
                    text=text,
                    summary=summary,
                    source=source,
                    author=author,
                    language=language,
                    categories_user=categories,
                    telegram_user_id=None
                )

                if result is None:
                    article_id = None
                    fingerprint = "duplicate"
                    status = "duplicate"
                    message = "Article already exists (duplicate content)"
                else:
                    article_id, fingerprint = result
                    status = "created"
                    message = "Article created successfully"

            except Exception as db_error:
                logger.error(f"Database error: {db_error}")
                raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        else:
            raise HTTPException(status_code=503, detail="Database not available")

        return {
            "success": True,
            "article_id": article_id,
            "fingerprint": fingerprint,
            "categories": categories,
            "status": status,
            "message": message,
            "processing_time": "fast",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in fast endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/n8n/status")
async def n8n_status(auth: bool = Depends(verify_api_key)):
    """Get API status for n8n monitoring"""
    try:
        global db_manager
        
        if db_manager:
            try:
                async with db_manager.pool.acquire() as conn:
                    articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
                    users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                    n8n_articles = await conn.fetchval(
                        "SELECT COUNT(*) FROM articles WHERE source = 'n8n'"
                    )
                
                return {
                    "status": "healthy",
                    "database": "connected",
                    "articles_total": articles_count,
                    "users_total": users_count,
                    "n8n_articles": n8n_articles,
                    "api_version": "1.0.0",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as db_error:
                logger.error(f"Database error in n8n status: {db_error}")
                return {
                    "status": "degraded",
                    "database": "error",
                    "error": str(db_error),
                    "api_version": "1.0.0",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            return {
                "status": "unavailable",
                "database": "disconnected",
                "api_version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in n8n status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "api_version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }

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
