#!/usr/bin/env python3
"""
Test API server with authentication (no database required)
"""
from fastapi import FastAPI, HTTPException, Query, Path, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import timedelta

from auth import (
    verify_api_key, get_current_active_user, rate_limit_middleware,
    create_access_token, authenticate_user, User, Token
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Test Article Management API",
    description="Test API for authentication without database",
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

# Add rate limiting middleware
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Apply rate limiting to all requests"""
    await rate_limit_middleware(request)
    response = await call_next(request)
    return response

@app.get("/")
async def read_root():
    """Root endpoint"""
    return {"message": "Test API with Authentication", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "test-api-with-auth"}

@app.post("/api/auth/login", response_model=Token)
async def login_for_access_token(username: str = Query(...), password: str = Query(...)):
    """Login endpoint to get JWT token"""
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

@app.get("/api/public/articles")
async def get_public_articles(
    limit: int = Query(10, ge=1, le=50, description="Number of articles to return"),
    offset: int = Query(0, ge=0, description="Number of articles to skip"),
    category: Optional[str] = Query(None, description="Filter by category"),
    api_key: str = Depends(verify_api_key)
):
    """Get public articles (requires API key)"""
    # Mock data
    mock_articles = [
        {
            "id": 1,
            "title": "Test Article 1",
            "summary": "This is a test article",
            "source": "test.com",
            "author": "Test Author",
            "categories": ["Technology"],
            "created_at": "2024-01-01T00:00:00Z"
        },
        {
            "id": 2,
            "title": "Test Article 2",
            "summary": "Another test article",
            "source": "test.com",
            "author": "Test Author 2",
            "categories": ["Business"],
            "created_at": "2024-01-02T00:00:00Z"
        }
    ]
    
    return mock_articles[:limit]

@app.get("/api/articles")
async def get_articles(
    limit: int = Query(50, ge=1, le=100, description="Number of articles to return"),
    offset: int = Query(0, ge=0, description="Number of articles to skip"),
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_active_user)
):
    """Get articles with filtering options (requires JWT)"""
    # Mock data with more details
    mock_articles = [
        {
            "id": 1,
            "title": "Protected Article 1",
            "summary": "This is a protected test article",
            "source": "protected.com",
            "author": "Protected Author",
            "categories_user": ["Technology"],
            "categories_auto": ["AI", "Machine Learning"],
            "language": "en",
            "comments_count": 5,
            "likes_count": 10,
            "views_count": 100,
            "telegram_user_id": 123456789,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        },
        {
            "id": 2,
            "title": "Protected Article 2",
            "summary": "Another protected test article",
            "source": "protected.com",
            "author": "Protected Author 2",
            "categories_user": ["Business"],
            "categories_auto": ["Finance", "Startup"],
            "language": "en",
            "comments_count": 3,
            "likes_count": 7,
            "views_count": 50,
            "telegram_user_id": 987654321,
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z"
        }
    ]
    
    return mock_articles[:limit]

@app.get("/api/articles/{article_id}")
async def get_article(
    article_id: int = Path(..., description="Article ID"),
    current_user: User = Depends(get_current_active_user)
):
    """Get article by ID (requires JWT)"""
    if article_id == 1:
        return {
            "id": 1,
            "title": "Protected Article 1",
            "summary": "This is a protected test article",
            "source": "protected.com",
            "author": "Protected Author",
            "categories_user": ["Technology"],
            "categories_auto": ["AI", "Machine Learning"],
            "language": "en",
            "comments_count": 5,
            "likes_count": 10,
            "views_count": 100,
            "telegram_user_id": 123456789,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    else:
        raise HTTPException(status_code=404, detail="Article not found")

@app.get("/api/statistics")
async def get_statistics(current_user: User = Depends(get_current_active_user)):
    """Get general statistics (requires JWT)"""
    return {
        "total_articles": 2,
        "categories": {
            "Technology": 1,
            "Business": 1
        },
        "languages": {
            "en": 2
        },
        "top_sources": {
            "protected.com": 2
        }
    }

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=5002, log_level="info")
