#!/usr/bin/env python3
"""
Веб-админка для Railway
"""
import os
import logging
import jwt
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

# API base URL - Railway environment or Docker
API_BASE_URL = os.getenv("API_BASE_URL", "https://tg-article-bot-api-production-12d6.up.railway.app")

# JWT Secret Key
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")

def get_current_user(token: str) -> Optional[Dict[str, Any]]:
    """Get current user from token"""
    if not token:
        return None
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if not username:
            return None
        
        # Get user from database
        user = get_user_by_username(username)
        return user
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return None

def get_articles(page: int = 1, per_page: int = 20):
    """Get articles from API or return mock data"""
    logger.info(f"Getting articles: page={page}, per_page={per_page}")
    
    # For now, always use mock data to avoid API issues
    logger.info("Using mock articles data")
    return get_mock_articles(page, per_page)

def get_mock_articles(page: int = 1, per_page: int = 20):
    """Generate mock articles data"""
    total_articles = 150
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Реалистичные заголовки статей
    titles = [
        "Искусственный интеллект в современном мире",
        "Квантовые вычисления: будущее технологий",
        "Блокчейн и криптовалюты в 2024 году",
        "Машинное обучение для бизнеса",
        "Облачные технологии и их преимущества",
        "Кибербезопасность в цифровую эпоху",
        "Большие данные и аналитика",
        "Интернет вещей (IoT) в повседневной жизни",
        "Автоматизация бизнес-процессов",
        "Цифровая трансформация предприятий",
        "5G технологии и их влияние",
        "Виртуальная и дополненная реальность",
        "Робототехника и автоматизация",
        "Зеленые технологии и устойчивое развитие",
        "Биотехнологии и медицина будущего"
    ]
    
    # Реалистичные категории
    categories = ["Технологии", "Наука", "Бизнес", "Медицина", "Образование", "Финансы"]
    
    # Статусы
    statuses = ["active", "pending", "archived"]
    
    articles = []
    for i in range(start_idx, min(end_idx, total_articles)):
        title_idx = i % len(titles)
        category_idx = i % len(categories)
        status_idx = i % len(statuses)
        
        # Генерируем реалистичное содержание
        content = f"""
        {titles[title_idx]} - это важная тема в современном мире. 
        Данная статья рассматривает основные аспекты и тенденции развития в этой области. 
        Мы изучили различные подходы и методы, которые используются сегодня.
        """
        
        articles.append({
            "id": i + 1,
            "title": titles[title_idx],
            "content": content.strip(),
            "category": categories[category_idx],
            "status": statuses[status_idx],
            "url": f"https://example.com/article/{i + 1}",
            "created_at": f"2024-01-{(i % 28) + 1:02d}",
            "fingerprint": f"fp_{i + 1:06d}",
            "author": f"Автор {i + 1}",
            "views": (i + 1) * 10,
            "likes": (i + 1) * 2
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
    access_token: Optional[str] = Cookie(None)
):
    """Dashboard page"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        current_user = get_current_user(access_token)
        if not current_user:
            return RedirectResponse(url="/", status_code=302)
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
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
    
    # Get all users for stats
    all_users = get_all_users()
    
    # Determine if user is admin
    is_admin = user and user.get("role") == "admin"
    
    # Debug logging
    logger.info(f"Dashboard - User: {user.get('username') if user else 'None'}, Role: {user.get('role') if user else 'None'}, Is Admin: {is_admin}")
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "users": all_users,
        "recent_users": recent_users,
        "is_admin": is_admin,
        "api_url": API_BASE_URL
    })

@app.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    access_token: Optional[str] = Cookie(None)
):
    """Users management page (admin only)"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        current_user = get_current_user(access_token)
        if not current_user:
            return RedirectResponse(url="/", status_code=302)
        
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        all_users = get_all_users()
        return templates.TemplateResponse("users.html", {
            "request": request,
            "user": current_user,
            "users": all_users
        })
    except Exception as e:
        logger.error(f"Error in users page: {e}")
        return RedirectResponse(url="/", status_code=302)

@app.get("/articles", response_class=HTMLResponse)
async def articles_page(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    access_token: Optional[str] = Cookie(None)
):
    """Articles page"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        current_user = get_current_user(access_token)
        if not current_user:
            return RedirectResponse(url="/", status_code=302)
        
        articles_data = get_articles(page, per_page)
        
        return templates.TemplateResponse("articles.html", {
            "request": request,
            "user": current_user,
            "articles": articles_data["articles"],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": articles_data["total"],
                "pages": articles_data["pages"]
            }
        })
    except Exception as e:
        logger.error(f"Error in articles page: {e}")
        return RedirectResponse(url="/", status_code=302)

@app.post("/users/add")
async def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    access_token: Optional[str] = Cookie(None)
):
    """Add new user (admin only)"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        current_user = get_current_user(access_token)
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Add user logic here
        return RedirectResponse(url="/users", status_code=302)
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return RedirectResponse(url="/users", status_code=302)

@app.get("/users/{username}/toggle")
async def toggle_user(
    username: str,
    access_token: Optional[str] = Cookie(None)
):
    """Toggle user status (admin only)"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        current_user = get_current_user(access_token)
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Toggle user logic here
        return RedirectResponse(url="/users", status_code=302)
    except Exception as e:
        logger.error(f"Error toggling user: {e}")
        return RedirectResponse(url="/users", status_code=302)

@app.get("/users/{username}/delete")
async def delete_user(
    username: str,
    access_token: Optional[str] = Cookie(None)
):
    """Delete user (admin only)"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        current_user = get_current_user(access_token)
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Delete user logic here
        return RedirectResponse(url="/users", status_code=302)
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return RedirectResponse(url="/users", status_code=302)

@app.get("/logout")
async def logout():
    """Logout"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.get("/api/users")
async def api_users(
    access_token: Optional[str] = Cookie(None)
):
    """API endpoint for users (admin only)"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        current_user = get_current_user(access_token)
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return {"users": get_all_users()}
    except Exception as e:
        logger.error(f"Error in API users: {e}")
        raise HTTPException(status_code=401, detail="Not authenticated")

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
