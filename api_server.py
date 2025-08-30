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

# Create FastAPI app
app = FastAPI(
    title="Railway API",
    description="API for Railway deployment",
    version="1.0.0"
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
    logger.info("Test endpoint called")
    return {
        "message": "Test endpoint works!",
        "port": os.getenv("PORT", "not set")
    }

@app.post("/articles")
async def create_article(article_data: dict):
    """Create new article with basic categorization"""
    try:
        text = article_data.get('text', '')
        title = article_data.get('title')
        source = article_data.get('source')
        
        logger.info(f"Creating article: {title}")
        
        if not text:
            return {"error": "Article text is required"}
        
        # Basic categorization
        categories = await basic_categorize(text)
        
        # Simulate saving (no database in simple version)
        article_id = 1  # Mock ID
        
        response_data = {
            "article_id": article_id,
            "fingerprint": "mock-fingerprint",
            "categories": categories,
            "summary": "Mock summary",
            "status": "created",
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
