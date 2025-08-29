#!/usr/bin/env python3
"""
Легкий ML Service с внешними API
"""
import logging
import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Light ML Article Processing Service",
    description="Service using external APIs for article processing",
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

class DetailedCategorizationResponse(BaseModel):
    basic_categorization: CategorizationResponse
    huggingface_categorization: Optional[CategorizationResponse] = None
    openai_categorization: Optional[CategorizationResponse] = None
    final_categorization: CategorizationResponse
    processing_methods: List[str]

class LightMLProcessor:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
        logger.info("Light ML Processor initialized")
    
    async def categorize_article(self, text: str, title: str = None) -> CategorizationResponse:
        """Категоризация статьи через внешние API (обратная совместимость)"""
        detailed_result = await self.categorize_article_detailed(text, title)
        return detailed_result.final_categorization

    async def categorize_article_detailed(self, text: str, title: str = None) -> DetailedCategorizationResponse:
        """Подробная категоризация статьи всеми доступными методами"""
        processing_methods = []
        
        # Всегда выполняем базовую категоризацию
        basic_result = await self._basic_categorization(text)
        processing_methods.append("basic_keywords")
        
        # Пытаемся Hugging Face категоризацию
        huggingface_result = None
        try:
            if self.huggingface_token:
                huggingface_result = await self._huggingface_categorization(text)
                processing_methods.append("huggingface_api")
        except Exception as e:
            logger.warning(f"Hugging Face categorization failed: {e}")
        
        # Пытаемся OpenAI категоризацию
        openai_result = None
        try:
            if self.openai_api_key:
                openai_result = await self._openai_categorization(text, title)
                processing_methods.append("openai_api")
        except Exception as e:
            logger.warning(f"OpenAI categorization failed: {e}")
        
        # Определяем финальную категоризацию
        final_result = self._combine_categorizations(basic_result, huggingface_result, openai_result)
        
        return DetailedCategorizationResponse(
            basic_categorization=basic_result,
            huggingface_categorization=huggingface_result,
            openai_categorization=openai_result,
            final_categorization=final_result,
            processing_methods=processing_methods
        )
    
    async def _openai_categorization(self, text: str, title: str = None) -> CategorizationResponse:
        """Категоризация через OpenAI API"""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        prompt = f"""
        Analyze this article and provide JSON response with:
        - categories: array of 3-5 relevant categories
        - language: detected language code (en, ru, etc.)
        - summary: brief summary (max 100 words)
        - confidence: confidence score (0-1)
        
        Title: {title or 'No title'}
        Text: {text[:1000]}...
        
        Respond only with valid JSON.
        """
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3
        )
        
        result = response.choices[0].message.content
        
        try:
            # Пытаемся парсить JSON
            data = json.loads(result)
            return CategorizationResponse(
                categories=data.get('categories', ['General']),
                confidence=data.get('confidence', 0.8),
                language=data.get('language', 'en'),
                summary=data.get('summary')
            )
        except json.JSONDecodeError:
            # Fallback если JSON не парсится
            return CategorizationResponse(
                categories=['Technology', 'News', 'Analysis'],
                confidence=0.7,
                language='en',
                summary=result[:100] if result else None
            )
    
    async def _huggingface_categorization(self, text: str) -> CategorizationResponse:
        """Категоризация через Hugging Face API"""
        if not self.huggingface_token:
            raise Exception("Hugging Face token not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
                headers={"Authorization": f"Bearer {self.huggingface_token}"},
                json={
                    "inputs": text[:500],
                    "parameters": {
                        "candidate_labels": [
                            "Technology", "Business", "Politics", "Sports", 
                            "Entertainment", "Science", "Health", "Education"
                        ]
                    }
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return CategorizationResponse(
                    categories=[data['labels'][0]] if data['labels'] else ['General'],
                    confidence=data.get('scores', [0.5])[0],
                    language='en',
                    summary=None
                )
            else:
                raise Exception(f"Hugging Face API error: {response.status_code}")
    
    async def _basic_categorization(self, text: str) -> CategorizationResponse:
        """Базовая категоризация по ключевым словам"""
        text_lower = text.lower()
        
        categories = []
        
        # Technology (английские и русские слова)
        tech_words = ['tech', 'technology', 'software', 'ai', 'machine learning', 'programming', 
                     'искусственный интеллект', 'ии', 'программирование', 'технология', 'технологии', 
                     'алгоритм', 'алгоритмы', 'машинное обучение', 'нейросеть', 'нейросети']
        if any(word in text_lower for word in tech_words):
            categories.append('Technology')
        
        # News (английские и русские слова)
        news_words = ['news', 'update', 'announcement', 'breaking', 'новости', 'новость', 
                     'обновление', 'анонс', 'объявление']
        if any(word in text_lower for word in news_words):
            categories.append('News')
        
        # Analysis (английские и русские слова)
        analysis_words = ['analysis', 'review', 'opinion', 'commentary', 'анализ', 'обзор', 
                         'мнение', 'комментарий', 'исследование']
        if any(word in text_lower for word in analysis_words):
            categories.append('Analysis')
        
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
        
        # Sports (английские и русские слова)
        sports_words = ['sport', 'football', 'basketball', 'tennis', 'спорт', 'футбол', 
                       'баскетбол', 'теннис', 'игра', 'соревнование']
        if any(word in text_lower for word in sports_words):
            categories.append('Sports')
        
        # Education (английские и русские слова)
        education_words = ['education', 'learning', 'study', 'course', 'образование', 'обучение', 
                          'изучение', 'курс', 'учебный', 'образовательный']
        if any(word in text_lower for word in education_words):
            categories.append('Education')
        
        if not categories:
            categories = ['General']
        
        return CategorizationResponse(
            categories=categories,
            confidence=0.6,
            language='ru' if any(ord(c) > 127 for c in text) else 'en',
            summary=None
        )
    
    def _combine_categorizations(self, basic_result: CategorizationResponse, 
                                huggingface_result: Optional[CategorizationResponse] = None,
                                openai_result: Optional[CategorizationResponse] = None) -> CategorizationResponse:
        """Объединяет результаты всех методов категоризации"""
        
        # Приоритет: OpenAI > Hugging Face > Basic
        if openai_result:
            return openai_result
        elif huggingface_result:
            return huggingface_result
        else:
            return basic_result

# Global ML processor
ml_processor = LightMLProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "light-ml-processor",
        "apis": {
            "openai": bool(ml_processor.openai_api_key),
            "huggingface": bool(ml_processor.huggingface_token)
        }
    }

@app.post("/categorize", response_model=CategorizationResponse)
async def categorize_article(request: ArticleRequest):
    """Категоризация статьи"""
    try:
        result = await ml_processor.categorize_article(request.text, request.title)
        return result
    except Exception as e:
        logger.error(f"Error categorizing article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/categorize-detailed", response_model=DetailedCategorizationResponse)
async def categorize_article_detailed(request: ArticleRequest):
    """Подробная категоризация статьи всеми методами"""
    try:
        result = await ml_processor.categorize_article_detailed(request.text, request.title)
        return result
    except Exception as e:
        logger.error(f"Error in detailed categorization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_article(request: ArticleRequest):
    """Полный анализ статьи"""
    try:
        categorization = await ml_processor.categorize_article(request.text, request.title)
        
        return {
            "categorization": categorization,
            "word_count": len(request.text.split()),
            "estimated_reading_time": len(request.text.split()) // 200,
            "has_summary": bool(categorization.summary),
            "processing_method": "external_api"
        }
    except Exception as e:
        logger.error(f"Error analyzing article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
