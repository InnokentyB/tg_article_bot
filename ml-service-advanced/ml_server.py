#!/usr/bin/env python3
"""
Продвинутый ML Service с возможностью дообучения
"""
import logging
import os
import json
import pickle
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Advanced ML Article Processing Service",
    description="Service with retraining capabilities and advanced categorization",
    version="2.0.0"
)

# Models directory
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

class ArticleRequest(BaseModel):
    text: str
    title: Optional[str] = None
    source: Optional[str] = None

class CategorizationResponse(BaseModel):
    categories: List[str]
    confidence: float
    language: str
    summary: Optional[str] = None
    model_version: str
    processing_time: float

class DetailedCategorizationResponse(BaseModel):
    basic_categorization: CategorizationResponse
    huggingface_categorization: Optional[CategorizationResponse] = None
    openai_categorization: Optional[CategorizationResponse] = None
    ml_model_categorization: Optional[CategorizationResponse] = None
    final_categorization: CategorizationResponse
    processing_methods: List[str]

class TrainingData(BaseModel):
    text: str
    categories: List[str]
    confidence: Optional[float] = None

class TrainingRequest(BaseModel):
    articles: List[TrainingData]
    model_name: Optional[str] = "default"

class TrainingResponse(BaseModel):
    status: str
    model_version: str
    accuracy: float
    training_samples: int
    categories: List[str]
    training_time: float

class ModelInfo(BaseModel):
    model_name: str
    version: str
    accuracy: float
    training_samples: int
    categories: List[str]
    last_trained: str
    is_active: bool

class AdvancedMLProcessor:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
        
        # ML Model components
        self.vectorizer = None
        self.classifier = None
        self.model_version = "1.0.0"
        self.categories = []
        self.training_data = []
        
        # Load or initialize model
        self._load_model()
        
        logger.info("Advanced ML Processor initialized")
    
    def _load_model(self):
        """Загрузка обученной модели"""
        model_path = MODELS_DIR / "article_classifier.pkl"
        if model_path.exists():
            try:
                model_data = joblib.load(model_path)
                self.vectorizer = model_data['vectorizer']
                self.classifier = model_data['classifier']
                self.model_version = model_data.get('version', '1.0.0')
                self.categories = model_data.get('categories', [])
                self.training_data = model_data.get('training_data', [])
                logger.info(f"Model loaded: version {self.model_version}, categories: {len(self.categories)}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self._initialize_default_model()
        else:
            self._initialize_default_model()
    
    def _initialize_default_model(self):
        """Инициализация модели по умолчанию"""
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words='english'
        )
        self.classifier = MultinomialNB()
        self.categories = ['Technology', 'Business', 'Science', 'Health', 'Education', 'Entertainment', 'Sports', 'Politics']
        self.training_data = []
        logger.info("Default model initialized")
    
    def _save_model(self):
        """Сохранение модели"""
        model_data = {
            'vectorizer': self.vectorizer,
            'classifier': self.classifier,
            'version': self.model_version,
            'categories': self.categories,
            'training_data': self.training_data,
            'last_updated': datetime.now().isoformat()
        }
        
        model_path = MODELS_DIR / "article_classifier.pkl"
        joblib.dump(model_data, model_path)
        logger.info(f"Model saved: version {self.model_version}")
    
    async def categorize_article(self, text: str, title: str = None) -> CategorizationResponse:
        """Категоризация статьи (обратная совместимость)"""
        detailed_result = await self.categorize_article_detailed(text, title)
        return detailed_result.final_categorization

    async def categorize_article_detailed(self, text: str, title: str = None) -> DetailedCategorizationResponse:
        """Подробная категоризация статьи всеми доступными методами"""
        import time
        start_time = time.time()
        processing_methods = []
        
        # Базовая категоризация
        basic_result = await self._basic_categorization(text)
        processing_methods.append("basic_keywords")
        
        # ML Model категоризация
        ml_result = None
        try:
            ml_result = await self._ml_model_categorization(text)
            processing_methods.append("ml_model")
        except Exception as e:
            logger.warning(f"ML model categorization failed: {e}")
        
        # Hugging Face категоризация
        huggingface_result = None
        try:
            if self.huggingface_token:
                huggingface_result = await self._huggingface_categorization(text)
                processing_methods.append("huggingface_api")
        except Exception as e:
            logger.warning(f"Hugging Face categorization failed: {e}")
        
        # OpenAI категоризация
        openai_result = None
        try:
            if self.openai_api_key:
                openai_result = await self._openai_categorization(text, title)
                processing_methods.append("openai_api")
        except Exception as e:
            logger.warning(f"OpenAI categorization failed: {e}")
        
        # Определяем финальную категоризацию
        final_result = self._combine_categorizations(basic_result, ml_result, huggingface_result, openai_result)
        final_result.processing_time = time.time() - start_time
        
        return DetailedCategorizationResponse(
            basic_categorization=basic_result,
            huggingface_categorization=huggingface_result,
            openai_categorization=openai_result,
            ml_model_categorization=ml_result,
            final_categorization=final_result,
            processing_methods=processing_methods
        )
    
    async def _ml_model_categorization(self, text: str) -> CategorizationResponse:
        """Категоризация через обученную ML модель"""
        if not self.vectorizer or not self.classifier:
            raise Exception("ML model not available")
        
        # Подготовка текста
        full_text = text.lower()
        
        # Векторизация
        try:
            features = self.vectorizer.transform([full_text])
            probabilities = self.classifier.predict_proba(features)[0]
            predicted_idx = np.argmax(probabilities)
            confidence = float(probabilities[predicted_idx])
            
            # Получаем топ-3 категории
            top_indices = np.argsort(probabilities)[-3:][::-1]
            categories = [self.categories[i] for i in top_indices if probabilities[i] > 0.1]
            
            if not categories:
                categories = [self.categories[predicted_idx]]
            
            return CategorizationResponse(
                categories=categories,
                confidence=confidence,
                language="en",
                model_version=self.model_version
            )
        except Exception as e:
            logger.error(f"ML model prediction failed: {e}")
            raise
    
    async def _basic_categorization(self, text: str) -> CategorizationResponse:
        """Базовая категоризация по ключевым словам"""
        text_lower = text.lower()
        
        # Определение категорий по ключевым словам
        categories = []
        confidence = 0.5
        
        if any(word in text_lower for word in ['ai', 'artificial intelligence', 'machine learning', 'neural', 'algorithm', 'programming', 'software', 'tech', 'technology']):
            categories.append('Technology')
            confidence = 0.8
        
        if any(word in text_lower for word in ['business', 'company', 'startup', 'investment', 'market', 'finance', 'economy', 'entrepreneur']):
            categories.append('Business')
            confidence = 0.7
        
        if any(word in text_lower for word in ['science', 'research', 'study', 'experiment', 'discovery', 'scientific']):
            categories.append('Science')
            confidence = 0.7
        
        if any(word in text_lower for word in ['health', 'medical', 'medicine', 'disease', 'treatment', 'patient', 'doctor']):
            categories.append('Health')
            confidence = 0.7
        
        if any(word in text_lower for word in ['education', 'learning', 'school', 'university', 'student', 'course', 'training']):
            categories.append('Education')
            confidence = 0.7
        
        if any(word in text_lower for word in ['movie', 'film', 'music', 'game', 'entertainment', 'celebrity']):
            categories.append('Entertainment')
            confidence = 0.6
        
        if any(word in text_lower for word in ['sport', 'football', 'basketball', 'tennis', 'olympic', 'championship']):
            categories.append('Sports')
            confidence = 0.6
        
        if any(word in text_lower for word in ['politics', 'government', 'election', 'president', 'minister', 'policy']):
            categories.append('Politics')
            confidence = 0.6
        
        if not categories:
            categories = ['General']
            confidence = 0.3
        
        return CategorizationResponse(
            categories=categories,
            confidence=confidence,
            language="en",
            model_version="basic"
        )
    
    async def _huggingface_categorization(self, text: str) -> CategorizationResponse:
        """Категоризация через Hugging Face API"""
        if not self.huggingface_token:
            raise Exception("Hugging Face token not available")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
                    headers={"Authorization": f"Bearer {self.huggingface_token}"},
                    json={"inputs": text[:500]},  # Ограничиваем длину
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary = result[0]['summary_text'] if result else None
                    
                    # Простая категоризация на основе summary
                    if summary:
                        return await self._basic_categorization(summary)
                    else:
                        return await self._basic_categorization(text)
                else:
                    raise Exception(f"Hugging Face API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Hugging Face API call failed: {e}")
            raise
    
    async def _openai_categorization(self, text: str, title: str = None) -> CategorizationResponse:
        """Категоризация через OpenAI API"""
        if not self.openai_api_key:
            raise Exception("OpenAI API key not available")
        
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        prompt = f"""
        Analyze this article and provide JSON response with:
        - categories: list of 1-3 most relevant categories from: Technology, Business, Science, Health, Education, Entertainment, Sports, Politics
        - confidence: confidence score (0.0-1.0)
        - summary: brief summary (max 100 words)
        
        Article title: {title or 'No title'}
        Article text: {text[:1000]}...
        
        Respond only with valid JSON.
        """
        
        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            # Парсим JSON ответ
            try:
                result = json.loads(content)
                return CategorizationResponse(
                    categories=result.get('categories', ['General']),
                    confidence=result.get('confidence', 0.5),
                    language="en",
                    summary=result.get('summary'),
                    model_version="openai"
                )
            except json.JSONDecodeError:
                # Fallback к базовой категоризации
                return await self._basic_categorization(text)
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _combine_categorizations(self, basic_result, ml_result=None, huggingface_result=None, openai_result=None) -> CategorizationResponse:
        """Объединение результатов всех методов категоризации"""
        results = [basic_result]
        if ml_result:
            results.append(ml_result)
        if huggingface_result:
            results.append(huggingface_result)
        if openai_result:
            results.append(openai_result)
        
        # Подсчитываем голоса для каждой категории
        category_votes = {}
        total_confidence = 0
        
        for result in results:
            for category in result.categories:
                if category not in category_votes:
                    category_votes[category] = 0
                category_votes[category] += result.confidence
                total_confidence += result.confidence
        
        # Выбираем топ категории
        sorted_categories = sorted(category_votes.items(), key=lambda x: x[1], reverse=True)
        final_categories = [cat for cat, votes in sorted_categories[:3] if votes > 0.1]
        
        if not final_categories:
            final_categories = ['General']
        
        # Средняя уверенность
        avg_confidence = total_confidence / len(results) if results else 0.5
        
        return CategorizationResponse(
            categories=final_categories,
            confidence=min(avg_confidence, 0.95),
            language="en",
            model_version="combined"
        )
    
    async def train_model(self, training_data: List[TrainingData]) -> TrainingResponse:
        """Дообучение модели"""
        import time
        start_time = time.time()
        
        if not training_data:
            raise HTTPException(status_code=400, detail="No training data provided")
        
        # Подготовка данных
        texts = []
        labels = []
        
        for item in training_data:
            texts.append(item.text.lower())
            # Берем первую категорию как основную метку
            labels.append(item.categories[0] if item.categories else 'General')
        
        # Обновляем список категорий
        unique_categories = list(set(labels))
        self.categories = list(set(self.categories + unique_categories))
        
        # Добавляем новые данные к существующим
        self.training_data.extend(training_data)
        
        # Обучение модели
        try:
            # Векторизация
            X = self.vectorizer.fit_transform(texts)
            y = labels
            
            # Обучение классификатора
            self.classifier.fit(X, y)
            
            # Оценка качества
            y_pred = self.classifier.predict(X)
            accuracy = accuracy_score(y, y_pred)
            
            # Обновляем версию модели
            self.model_version = f"{self.model_version.split('.')[0]}.{int(self.model_version.split('.')[1]) + 1}.0"
            
            # Сохраняем модель
            self._save_model()
            
            training_time = time.time() - start_time
            
            return TrainingResponse(
                status="success",
                model_version=self.model_version,
                accuracy=accuracy,
                training_samples=len(texts),
                categories=self.categories,
                training_time=training_time
            )
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")
    
    def get_model_info(self) -> ModelInfo:
        """Информация о модели"""
        return ModelInfo(
            model_name="article_classifier",
            version=self.model_version,
            accuracy=0.0,  # Нужно будет добавить валидационный набор
            training_samples=len(self.training_data),
            categories=self.categories,
            last_trained=datetime.now().isoformat(),
            is_active=True
        )

# Инициализация процессора
ml_processor = AdvancedMLProcessor()

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Advanced ML Article Processing Service",
        "version": "2.0.0",
        "status": "ok",
        "features": ["categorization", "retraining", "multiple_methods"]
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "model_version": ml_processor.model_version}

@app.post("/categorize", response_model=CategorizationResponse)
async def categorize_article(request: ArticleRequest):
    """Категоризация статьи (простая)"""
    return await ml_processor.categorize_article(request.text, request.title)

@app.post("/categorize-detailed", response_model=DetailedCategorizationResponse)
async def categorize_article_detailed(request: ArticleRequest):
    """Подробная категоризация статьи"""
    return await ml_processor.categorize_article_detailed(request.text, request.title)

@app.post("/train", response_model=TrainingResponse)
async def train_model(request: TrainingRequest):
    """Дообучение модели"""
    return await ml_processor.train_model(request.articles)

@app.get("/model-info", response_model=ModelInfo)
async def get_model_info():
    """Информация о модели"""
    return ml_processor.get_model_info()

@app.post("/train-background")
async def train_model_background(request: TrainingRequest, background_tasks: BackgroundTasks):
    """Дообучение модели в фоновом режиме"""
    background_tasks.add_task(ml_processor.train_model, request.articles)
    return {"status": "training_started", "message": "Model training started in background"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
