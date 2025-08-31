#!/usr/bin/env python3
"""
Веб-админка для Railway
"""
import os
import logging
from fastapi import FastAPI, Request, Form, HTTPException, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import auth module
from auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user, 
    get_current_active_user,
    fake_users_db,
    get_user_by_username,
    get_all_users
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Article Bot Web Admin",
    description="Веб-админка для управления статьями и пользователями",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# API base URL - Railway environment
API_BASE_URL = os.getenv("API_BASE_URL", "https://tg-article-bot-api-production-12d6.up.railway.app")

def create_mock_token(token: str) -> Dict[str, Any]:
    """Create mock token for auth dependency"""
    return {"access_token": token}

def get_articles(page: int = 1, per_page: int = 20):
    """Get articles from API or return mock data"""
    try:
        # Try to get from API
        response = requests.get(
            f"{API_BASE_URL}/api/articles",
            params={"page": page, "per_page": per_page},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Failed to get articles from API: {e}")
    
    # Return mock data if API fails
    return get_mock_articles(page, per_page)

def get_mock_articles(page: int = 1, per_page: int = 20):
    """Generate mock articles data"""
    total_articles = 150
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    articles = []
    for i in range(start_idx, min(end_idx, total_articles)):
        articles.append({
            "id": i + 1,
            "title": f"Статья {i + 1}",
            "content": f"Содержание статьи {i + 1}. Это тестовый контент для демонстрации пагинации.",
            "category": ["Технологии", "Наука", "Бизнес"][i % 3],
            "status": ["active", "pending", "archived"][i % 3],
            "date": f"2024-01-{(i % 28) + 1:02d}",
            "fingerprint": f"fp_{i + 1:06d}"
        })
    
    return {
        "articles": articles,
        "total": total_articles,
        "page": page,
        "per_page": per_page,
        "pages": (total_articles + per_page - 1) // per_page
    }

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Handle login"""
    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Неверный логин или пароль"}
        )
    
    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: Dict = Depends(lambda: get_current_user(Cookie("access_token")))
):
    """Dashboard page"""
    if not current_user:
        return RedirectResponse(url="/", status_code=302)
    
    # Get user info
    user = get_user_by_username(current_user["username"])
    
    # Get stats
    try:
        stats_response = requests.get(f"{API_BASE_URL}/api/stats", timeout=5)
        stats = stats_response.json() if stats_response.status_code == 200 else {}
    except:
        stats = {"total_articles": 150, "total_users": 5, "active_articles": 120}
    
    # Get recent users (admin only)
    recent_users = []
    if user and user.get("role") == "admin":
        recent_users = get_all_users()[:5]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "recent_users": recent_users
    })

@app.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    current_user: Dict = Depends(lambda: get_current_user(Cookie("access_token")))
):
    """Users management page (admin only)"""
    if not current_user:
        return RedirectResponse(url="/", status_code=302)
    
    user = get_user_by_username(current_user["username"])
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    all_users = get_all_users()
    return templates.TemplateResponse("users.html", {
        "request": request,
        "user": user,
        "users": all_users
    })

@app.get("/articles", response_class=HTMLResponse)
async def articles_page(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    current_user: Dict = Depends(lambda: get_current_user(Cookie("access_token")))
):
    """Articles page"""
    if not current_user:
        return RedirectResponse(url="/", status_code=302)
    
    user = get_user_by_username(current_user["username"])
    articles_data = get_articles(page, per_page)
    
    return templates.TemplateResponse("articles.html", {
        "request": request,
        "user": user,
        "articles": articles_data["articles"],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": articles_data["total"],
            "pages": articles_data["pages"]
        }
    })

@app.post("/users/add")
async def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    current_user: Dict = Depends(lambda: get_current_user(Cookie("access_token")))
):
    """Add new user (admin only)"""
    if not current_user:
        return RedirectResponse(url="/", status_code=302)
    
    user = get_user_by_username(current_user["username"])
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Add user logic here
    return RedirectResponse(url="/users", status_code=302)

@app.get("/users/{username}/toggle")
async def toggle_user(
    username: str,
    current_user: Dict = Depends(lambda: get_current_user(Cookie("access_token")))
):
    """Toggle user status (admin only)"""
    if not current_user:
        return RedirectResponse(url="/", status_code=302)
    
    user = get_user_by_username(current_user["username"])
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Toggle user logic here
    return RedirectResponse(url="/users", status_code=302)

@app.get("/users/{username}/delete")
async def delete_user(
    username: str,
    current_user: Dict = Depends(lambda: get_current_user(Cookie("access_token")))
):
    """Delete user (admin only)"""
    if not current_user:
        return RedirectResponse(url="/", status_code=302)
    
    user = get_user_by_username(current_user["username"])
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Delete user logic here
    return RedirectResponse(url="/users", status_code=302)

@app.get("/logout")
async def logout():
    """Logout"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.get("/api/users")
async def api_users(
    current_user: Dict = Depends(lambda: get_current_user(Cookie("access_token")))
):
    """API endpoint for users (admin only)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = get_user_by_username(current_user["username"])
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {"users": get_all_users()}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "web-admin",
        "api_url": API_BASE_URL
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get port from Railway environment
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"Starting Web Admin on port {port}")
    logger.info(f"API Base URL: {API_BASE_URL}")
    
    uvicorn.run(
        "web_admin_railway:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
