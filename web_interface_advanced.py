#!/usr/bin/env python3
"""
Веб-интерфейс для дообучения ML модели
"""
import logging
import os
import asyncio
from typing import List, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Training Web Interface",
    description="Web interface for ML model training",
    version="1.0.0"
)

# Configuration
API_URL = os.getenv('API_URL', 'http://localhost:5000')
ML_SERVICE_URL = os.getenv('ML_SERVICE_URL', 'http://localhost:8001')

# Templates
templates = Jinja2Templates(directory="templates")

class TrainingData(BaseModel):
    text: str
    categories: List[str]

class TrainingRequest(BaseModel):
    articles: List[TrainingData]

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/train", response_class=HTMLResponse)
async def train_page(request: Request):
    """Страница дообучения"""
    return templates.TemplateResponse("train.html", {"request": request})

@app.get("/model-info", response_class=HTMLResponse)
async def model_info_page(request: Request):
    """Страница информации о модели"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ML_SERVICE_URL}/model-info", timeout=10.0)
            if response.status_code == 200:
                model_info = response.json()
                return templates.TemplateResponse("model_info.html", {
                    "request": request,
                    "model_info": model_info
                })
            else:
                return templates.TemplateResponse("model_info.html", {
                    "request": request,
                    "model_info": None,
                    "error": "Failed to get model info"
                })
    except Exception as e:
        return templates.TemplateResponse("model_info.html", {
            "request": request,
            "model_info": None,
            "error": str(e)
        })

@app.post("/api/train")
async def train_model(request: Request):
    """API для дообучения модели"""
    try:
        form_data = await request.form()
        
        # Парсим данные из формы
        articles = []
        i = 0
        while f"text_{i}" in form_data:
            text = form_data[f"text_{i}"]
            categories_str = form_data.get(f"categories_{i}", "")
            categories = [cat.strip() for cat in categories_str.split(",") if cat.strip()]
            
            if text and categories:
                articles.append({
                    "text": text,
                    "categories": categories
                })
            i += 1
        
        if not articles:
            raise HTTPException(status_code=400, detail="No training data provided")
        
        # Отправляем запрос на обучение
        training_request = TrainingRequest(articles=articles)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/ml/train",
                json=training_request.dict(),
                timeout=300.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=500, detail="Training failed")
                
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/model-info")
async def get_model_info():
    """API для получения информации о модели"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ML_SERVICE_URL}/model-info", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=500, detail="Failed to get model info")
    except Exception as e:
        logger.error(f"Model info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test-categorization")
async def test_categorization(request: Request):
    """API для тестирования категоризации"""
    try:
        form_data = await request.form()
        text = form_data.get("text", "")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        # Отправляем запрос на категоризацию
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/articles",
                json={"text": text, "title": "Test Article"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=500, detail="Categorization failed")
                
    except Exception as e:
        logger.error(f"Categorization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
