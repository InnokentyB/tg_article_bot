#!/usr/bin/env python3
"""
ML Service для обработки статей
"""
import logging
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import httpx

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Article Processing Service",
    description="Service for article categorization and analysis",
    version="1.0.0"
)

class ArticleRequest(BaseModel):
    text: str
    title: Optional[str] = None
    source: Optional[str] = None

class CategorizationResponse(BaseModel):
    categories: List[str]
    confidence: float
    language: str
    summary: Optional[str] = None

class MLProcessor:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        logger.info("ML Processor initialized")
    
    async def categorize_article(self, text: str, title: str = None) -> CategorizationResponse:
        """Категоризация статьи с помощью OpenAI"""
        try:
            if not self.openai_api_key:
                # Fallback to basic categorization
                return await self._basic_categorization(text)
            
            # OpenAI categorization
            return await self._openai_categorization(text, title)
        except Exception as e:
            logger.error(f"Error in categorization: {e}")
            return await self._basic_categorization(text)
    
    async def _openai_categorization(self, text: str, title: str = None) -> CategorizationResponse:
        """Категоризация через OpenAI"""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        prompt = f"""
        Analyze this article and provide:
        1. 3-5 relevant categories (comma-separated)
        2. Language detection
        3. Brief summary (max 100 words)
        
        Title: {title or 'No title'}
        Text: {text[:1000]}...
        """
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        
        result = response.choices[0].message.content
        
        # Parse response (simplified)
        categories = ["Technology", "News", "Analysis"]  # Default
        if "categories:" in result.lower():
            cat_part = result.split("categories:")[1].split("\n")[0]
            categories = [cat.strip() for cat in cat_part.split(",")]
        
        return CategorizationResponse(
            categories=categories[:5],
            confidence=0.85,
            language="en",
            summary=result[:100] if len(result) > 100 else result
        )
    
    async def _basic_categorization(self, text: str) -> CategorizationResponse:
        """Базовая категоризация без ML"""
        # Simple keyword-based categorization
        text_lower = text.lower()
        
        categories = []
        if any(word in text_lower for word in ['tech', 'technology', 'software', 'ai', 'machine learning']):
            categories.append('Technology')
        if any(word in text_lower for word in ['news', 'update', 'announcement']):
            categories.append('News')
        if any(word in text_lower for word in ['analysis', 'review', 'opinion']):
            categories.append('Analysis')
        if any(word in text_lower for word in ['business', 'finance', 'economy']):
            categories.append('Business')
        if any(word in text_lower for word in ['health', 'medical', 'science']):
            categories.append('Health & Science')
        
        if not categories:
            categories = ['General']
        
        return CategorizationResponse(
            categories=categories,
            confidence=0.6,
            language="en",
            summary=None
        )

# Global ML processor
ml_processor = MLProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ml-article-processor"}

@app.post("/categorize", response_model=CategorizationResponse)
async def categorize_article(request: ArticleRequest):
    """Категоризация статьи"""
    try:
        result = await ml_processor.categorize_article(request.text, request.title)
        return result
    except Exception as e:
        logger.error(f"Error categorizing article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_article(request: ArticleRequest):
    """Полный анализ статьи"""
    try:
        categorization = await ml_processor.categorize_article(request.text, request.title)
        
        return {
            "categorization": categorization,
            "word_count": len(request.text.split()),
            "estimated_reading_time": len(request.text.split()) // 200,  # ~200 words per minute
            "has_summary": bool(categorization.summary)
        }
    except Exception as e:
        logger.error(f"Error analyzing article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
