#!/usr/bin/env python3
"""
Translation Service for Article Bot
Version: 1.0 - Initial translation service with OpenAI and Google Translate support
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import openai
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx
from deep_translator import GoogleTranslator
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
PORT = int(os.getenv("PORT", 8003))

# Initialize OpenAI
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    logger.info("OpenAI API key configured")
else:
    logger.warning("OpenAI API key not found")

# Google Translator will be initialized per request

# FastAPI app
app = FastAPI(
    title="Article Translation Service",
    description="Микросервис для перевода статей на английский язык",
    version="1.0.0"
)

# Pydantic models
class TranslationRequest(BaseModel):
    text: str
    source_language: str = "ru"
    target_language: str = "en"
    provider: str = "openai"  # "openai" or "google"
    preserve_formatting: bool = True

class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    confidence: Optional[float] = None
    timestamp: datetime

class ArticleTranslationRequest(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    source_language: str = "ru"
    target_language: str = "en"
    provider: str = "openai"

class ArticleTranslationResponse(BaseModel):
    original: Dict[str, str]
    translated: Dict[str, str]
    provider: str
    timestamp: datetime

# Translation functions
async def translate_with_openai(text: str, source_lang: str = "ru", target_lang: str = "en") -> Dict[str, Any]:
    """Translate text using OpenAI GPT"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        # Create a more sophisticated prompt for better translation
        prompt = f"""
Translate the following text from {source_lang} to {target_lang}. 
Preserve the original formatting, style, and tone. 
If the text contains technical terms or proper nouns, keep them accurate.
Provide a natural, fluent translation that reads well in {target_lang}.

Text to translate:
{text}

Translation:
"""
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a professional translator specializing in {source_lang} to {target_lang} translation. Provide accurate, natural translations while preserving formatting and context."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        translated_text = response.choices[0].message.content.strip()
        
        return {
            "translated_text": translated_text,
            "confidence": 0.9,  # OpenAI generally provides high-quality translations
            "provider": "openai"
        }
        
    except Exception as e:
        logger.error(f"OpenAI translation error: {e}")
        raise HTTPException(status_code=500, detail=f"OpenAI translation failed: {str(e)}")

async def translate_with_google(text: str, source_lang: str = "ru", target_lang: str = "en") -> Dict[str, Any]:
    """Translate text using Google Translate via deep-translator"""
    try:
        # Handle long texts by splitting them
        max_length = 5000  # Google Translate limit
        if len(text) > max_length:
            # Split text into chunks
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            translated_chunks = []
            
            for chunk in chunks:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translated_chunk = translator.translate(chunk)
                translated_chunks.append(translated_chunk)
            
            translated_text = "".join(translated_chunks)
        else:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_text = translator.translate(text)
        
        return {
            "translated_text": translated_text,
            "confidence": 0.8,  # Default confidence for Google Translate
            "provider": "google"
        }
        
    except Exception as e:
        logger.error(f"Google Translate error: {e}")
        raise HTTPException(status_code=500, detail=f"Google Translate failed: {str(e)}")

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "translation-service",
        "version": "1.0.0",
        "providers": {
            "openai": bool(OPENAI_API_KEY),
            "google": True
        }
    }

@app.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """Translate text using specified provider"""
    logger.info(f"Translation request: {request.provider} {request.source_language}->{request.target_language}")
    
    try:
        if request.provider == "openai":
            result = await translate_with_openai(
                request.text, 
                request.source_language, 
                request.target_language
            )
        elif request.provider == "google":
            result = await translate_with_google(
                request.text, 
                request.source_language, 
                request.target_language
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported translation provider")
        
        return TranslationResponse(
            original_text=request.text,
            translated_text=result["translated_text"],
            source_language=request.source_language,
            target_language=request.target_language,
            provider=result["provider"],
            confidence=result.get("confidence"),
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@app.post("/translate/article", response_model=ArticleTranslationResponse)
async def translate_article(request: ArticleTranslationRequest):
    """Translate complete article (title, content, summary)"""
    logger.info(f"Article translation request: {request.provider}")
    
    try:
        translated_parts = {}
        original_parts = {
            "title": request.title,
            "content": request.content
        }
        
        if request.summary:
            original_parts["summary"] = request.summary
        
        # Translate each part
        for part_name, text in original_parts.items():
            if request.provider == "openai":
                result = await translate_with_openai(
                    text, 
                    request.source_language, 
                    request.target_language
                )
            elif request.provider == "google":
                result = await translate_with_google(
                    text, 
                    request.source_language, 
                    request.target_language
                )
            else:
                raise HTTPException(status_code=400, detail="Unsupported translation provider")
            
            translated_parts[part_name] = result["translated_text"]
        
        return ArticleTranslationResponse(
            original=original_parts,
            translated=translated_parts,
            provider=request.provider,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Article translation error: {e}")
        raise HTTPException(status_code=500, detail=f"Article translation failed: {str(e)}")

@app.get("/providers")
async def get_available_providers():
    """Get list of available translation providers"""
    return {
        "providers": [
            {
                "name": "openai",
                "available": bool(OPENAI_API_KEY),
                "description": "OpenAI GPT-based translation (high quality, context-aware)"
            },
            {
                "name": "google",
                "available": True,
                "description": "Google Translate (fast, reliable)"
            }
        ]
    }

@app.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "languages": {
            "ru": "Russian",
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting Translation Service on port {PORT}")
    logger.info(f"OpenAI available: {bool(OPENAI_API_KEY)}")
    logger.info(f"Google Translate available: True")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        reload=False
    )
