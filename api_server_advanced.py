#!/usr/bin/env python3
"""
Обновленный API сервер с интеграцией продвинутого ML сервиса
"""
import logging
import os
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
db_manager = None
ml_service_url = os.getenv('ML_SERVICE_URL', 'http://localhost:8001')

class ArticleRequest(BaseModel):
    text: str
    title: Optional[str] = None
    source: Optional[str] = None
    telegram_user_id: Optional[int] = None

class ArticleResponse(BaseModel):
    article_id: Optional[int]
    fingerprint: str
    categories: List[str]
    summary: Optional[str] = None
    status: str
    ml_service: str
    processing_methods: List[str]
    confidence: float
    model_version: str

class TrainingData(BaseModel):
    text: str
    categories: List[str]
    confidence: Optional[float] = None

class TrainingRequest(BaseModel):
    articles: List[TrainingData]
    model_name: Optional[str] = "default"

class ModelInfo(BaseModel):
    model_name: str
    version: str
    accuracy: float
    training_samples: int
    categories: List[str]
    last_trained: str
    is_active: bool

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global db_manager
    
    # Startup
    logger.info("Starting up Advanced API server...")
    
    # Log environment variables
    logger.info(f"PORT: {os.getenv('PORT', 'not set')}")
    logger.info(f"DATABASE_URL: {'set' if os.getenv('DATABASE_URL') else 'not set'}")
    logger.info(f"ML_SERVICE_URL: {ml_service_url}")
    
    # Initialize database
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Create tables if they don't exist
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
    
    # Check ML service
    await check_ml_service()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Advanced API server...")
    if db_manager:
        await db_manager.close()

app = FastAPI(
    title="Advanced Article Processing API",
    description="API with advanced ML integration and retraining capabilities",
    version="2.0.0",
    lifespan=lifespan
)

async def check_ml_service():
    """Проверка доступности ML сервиса"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ml_service_url}/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ ML Service available: version {data.get('model_version', 'unknown')}")
                return True
            else:
                logger.warning(f"⚠️ ML Service health check failed: {response.status_code}")
                return False
    except Exception as e:
        logger.warning(f"⚠️ ML Service not available: {e}")
        return False

async def call_ml_service(text: str, title: str = None) -> Dict[str, Any]:
    """Вызов ML сервиса для категоризации"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ml_service_url}/categorize-detailed",
                json={"text": text, "title": title},
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML Service error: {response.status_code}")
                raise HTTPException(status_code=500, detail="ML service error")
                
    except httpx.TimeoutException:
        logger.error("ML Service timeout")
        raise HTTPException(status_code=504, detail="ML service timeout")
    except Exception as e:
        logger.error(f"ML Service call failed: {e}")
        raise HTTPException(status_code=500, detail="ML service unavailable")

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Advanced Article Processing API",
        "version": "2.0.0",
        "status": "ok",
        "features": ["articles", "ml_integration", "retraining", "statistics"]
    }

@app.get("/health")
async def health():
    """Health check"""
    ml_status = await check_ml_service()
    db_status = "connected" if db_manager else "not connected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "ml_service": "available" if ml_status else "unavailable"
    }

@app.get("/api/health")
async def api_health():
    """API health check для Railway"""
    return await health()

@app.post("/articles", response_model=ArticleResponse)
async def create_article(request: ArticleRequest):
    """Создание новой статьи с продвинутой категоризацией"""
    global db_manager
    
    if not request.text:
        raise HTTPException(status_code=400, detail="Article text is required")
    
    try:
        # Вызов ML сервиса для категоризации
        ml_result = await call_ml_service(request.text, request.title)
        
        # Извлекаем результаты
        final_categorization = ml_result.get('final_categorization', {})
        categories = final_categorization.get('categories', ['General'])
        confidence = final_categorization.get('confidence', 0.5)
        summary = final_categorization.get('summary')
        model_version = final_categorization.get('model_version', 'unknown')
        processing_methods = ml_result.get('processing_methods', [])
        
        # Создаем fingerprint
        import hashlib
        content = f"{request.text}{request.title or ''}{request.source or ''}"
        fingerprint = hashlib.sha256(content.encode()).hexdigest()
        
        # Сохраняем в базу данных
        article_id = None
        if db_manager:
            try:
                # Создаем пользователя если нужно
                if request.telegram_user_id:
                    await db_manager.create_user(
                        telegram_user_id=request.telegram_user_id,
                        username=None,
                        first_name=None,
                        last_name=None
                    )
                
                # Сохраняем статью
                article_id = await db_manager.save_article(
                    title=request.title or "Без заголовка",
                    text=request.text,
                    summary=summary,
                    fingerprint=fingerprint,
                    source=request.source,
                    categories_auto=categories,
                    categories_advanced=ml_result,
                    telegram_user_id=request.telegram_user_id
                )
                
                logger.info(f"✅ Article saved to database: ID {article_id}")
                
            except Exception as db_error:
                logger.error(f"Database error: {db_error}")
                # Продолжаем без сохранения в БД
        else:
            logger.warning("⚠️ Database not available, skipping save")
        
        return ArticleResponse(
            article_id=article_id,
            fingerprint=fingerprint,
            categories=categories,
            summary=summary,
            status="created",
            ml_service="advanced",
            processing_methods=processing_methods,
            confidence=confidence,
            model_version=model_version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing article: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/articles")
async def get_articles(limit: int = 10, offset: int = 0):
    """Получение списка статей"""
    global db_manager
    
    if db_manager:
        try:
            articles = await db_manager.get_articles(limit=limit, offset=offset)
            count = await db_manager.get_articles_count()
            
            return {
                "articles": articles,
                "count": count,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise HTTPException(status_code=500, detail="Database error")
    else:
        # Fallback к mock данным
        return {
            "articles": [
                {
                    "id": 1,
                    "title": "Mock Article",
                    "summary": "This is a mock article",
                    "categories_auto": ["Technology"],
                    "created_at": datetime.now().isoformat()
                }
            ],
            "count": 1,
            "limit": limit,
            "offset": offset
        }

@app.get("/statistics")
async def get_statistics():
    """Получение статистики"""
    global db_manager
    
    if db_manager:
        try:
            articles_count = await db_manager.get_articles_count()
            users_count = await db_manager.get_users_count()
            
            return {
                "articles_count": articles_count,
                "users_count": users_count,
                "ml_service": "advanced",
                "database": "enabled",
                "status": "ok"
            }
        except Exception as e:
            logger.error(f"Database error: {e}")
            return {
                "articles_count": 0,
                "users_count": 0,
                "ml_service": "advanced",
                "database": "error",
                "status": "error"
            }
    else:
        return {
            "articles_count": 0,
            "users_count": 0,
            "ml_service": "advanced",
            "database": "disabled",
            "status": "ok"
        }

@app.post("/ml/train")
async def train_ml_model(request: TrainingRequest):
    """Дообучение ML модели"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ml_service_url}/train",
                json=request.dict(),
                timeout=300.0  # 5 минут для обучения
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML training error: {response.status_code}")
                raise HTTPException(status_code=500, detail="ML training failed")
                
    except httpx.TimeoutException:
        logger.error("ML training timeout")
        raise HTTPException(status_code=504, detail="ML training timeout")
    except Exception as e:
        logger.error(f"ML training call failed: {e}")
        raise HTTPException(status_code=500, detail="ML training unavailable")

@app.post("/ml/train-background")
async def train_ml_model_background(request: TrainingRequest):
    """Дообучение ML модели в фоновом режиме"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ml_service_url}/train-background",
                json=request.dict(),
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML background training error: {response.status_code}")
                raise HTTPException(status_code=500, detail="ML background training failed")
                
    except Exception as e:
        logger.error(f"ML background training call failed: {e}")
        raise HTTPException(status_code=500, detail="ML background training unavailable")

@app.get("/ml/model-info")
async def get_ml_model_info():
    """Информация о ML модели"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ml_service_url}/model-info",
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML model info error: {response.status_code}")
                raise HTTPException(status_code=500, detail="ML model info failed")
                
    except Exception as e:
        logger.error(f"ML model info call failed: {e}")
        raise HTTPException(status_code=500, detail="ML model info unavailable")

@app.get("/test")
async def test_endpoint():
    """Тестовый эндпоинт"""
    global db_manager
    
    db_status = "connected" if db_manager else "not connected"
    ml_status = await check_ml_service()
    
    return {
        "message": "Advanced API test endpoint works!",
        "port": os.getenv("PORT", "not set"),
        "database_url": "set" if os.getenv("DATABASE_URL") else "not set",
        "ml_service_url": ml_service_url,
        "database_status": db_status,
        "ml_service_status": "available" if ml_status else "unavailable"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
