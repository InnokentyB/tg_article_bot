#!/usr/bin/env python3
"""
Web Admin Interface for Article Management System
"""
from fastapi import FastAPI, HTTPException, Depends, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import logging
import os
from datetime import datetime

from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    get_current_admin_user, User, Token
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Article Management Admin",
    description="Web admin interface for article management system",
    version="1.0.0"
)

# Templates
templates = Jinja2Templates(directory="templates")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mock user database (same as in auth.py)
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@example.com",
        "hashed_password": "fakehashedpassword",
        "disabled": False,
        "role": "admin",
    },
    "user1": {
        "username": "user1",
        "full_name": "Regular User",
        "email": "user1@example.com",
        "hashed_password": "userpassword",
        "disabled": False,
        "role": "user",
    }
}

def get_user_by_username(username: str) -> Optional[User]:
    """Get user from database"""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(**user_dict)
    return None

def get_all_users() -> List[User]:
    """Get all users"""
    return [User(**user_data) for user_data in fake_users_db.values()]

def create_mock_token(token: str):
    """Create a mock token object for get_current_user"""
    class MockToken:
        def __init__(self, token):
            self.credentials = token
    return MockToken(token)

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
            {"request": request, "error": "Invalid username or password"}
        )
    
    # Create token
    access_token = create_access_token(data={"sub": user.username})
    
    # Redirect to dashboard
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, access_token: Optional[str] = Cookie(None)):
    """Dashboard page"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        # Verify token and get user
        from auth import get_current_user
        user = await get_current_user(create_mock_token(access_token))
        
        # Get user data
        user_data = get_user_by_username(user.username)
        if not user_data:
            return RedirectResponse(url="/", status_code=302)
        
        # Get all users for admin
        all_users = []
        if user_data.role == "admin":
            all_users = get_all_users()
        
        return templates.TemplateResponse(
            "dashboard.html", 
            {
                "request": request, 
                "user": user_data,
                "users": all_users,
                "is_admin": user_data.role == "admin"
            }
        )
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return RedirectResponse(url="/", status_code=302)

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, access_token: Optional[str] = Cookie(None)):
    """Users management page (admin only)"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        # Verify token and get admin user
        from auth import get_current_user
        user = await get_current_user(create_mock_token(access_token))
        admin_user = await get_current_admin_user(user)
        
        all_users = get_all_users()
        
        return templates.TemplateResponse(
            "users.html", 
            {
                "request": request, 
                "user": admin_user,
                "users": all_users
            }
        )
    except Exception as e:
        logger.error(f"Users page error: {e}")
        return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/users/add")
async def add_user(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    access_token: Optional[str] = Cookie(None)
):
    """Add new user (admin only)"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        # Verify admin access
        from auth import get_current_user
        user = await get_current_user(create_mock_token(access_token))
        admin_user = await get_current_admin_user(user)
        
        # Check if user already exists
        if username in fake_users_db:
            return templates.TemplateResponse(
                "users.html", 
                {
                    "request": request, 
                    "user": admin_user,
                    "users": get_all_users(),
                    "error": "User already exists"
                }
            )
        
        # Add new user
        fake_users_db[username] = {
            "username": username,
            "full_name": full_name,
            "email": email,
            "hashed_password": password,  # In production, hash this
            "disabled": False,
            "role": role,
        }
        
        return RedirectResponse(url="/users", status_code=302)
    except Exception as e:
        logger.error(f"Add user error: {e}")
        return RedirectResponse(url="/users", status_code=302)

@app.post("/users/{username}/toggle")
async def toggle_user(
    username: str,
    access_token: Optional[str] = Cookie(None)
):
    """Toggle user status (admin only)"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        # Verify admin access
        from auth import get_current_user
        user = await get_current_user(create_mock_token(access_token))
        admin_user = await get_current_admin_user(user)
        
        if username in fake_users_db:
            fake_users_db[username]["disabled"] = not fake_users_db[username]["disabled"]
        
        return RedirectResponse(url="/users", status_code=302)
    except Exception as e:
        logger.error(f"Toggle user error: {e}")
        return RedirectResponse(url="/users", status_code=302)

@app.post("/users/{username}/delete")
async def delete_user(
    username: str,
    access_token: Optional[str] = Cookie(None)
):
    """Delete user (admin only)"""
    if not access_token:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        # Verify admin access
        from auth import get_current_user
        user = await get_current_user(create_mock_token(access_token))
        admin_user = await get_current_admin_user(user)
        
        if username in fake_users_db and username != "admin":
            del fake_users_db[username]
        
        return RedirectResponse(url="/users", status_code=302)
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return RedirectResponse(url="/users", status_code=302)

@app.get("/logout")
async def logout():
    """Logout"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@app.get("/api/users")
async def api_get_users(current_user: User = Depends(get_current_admin_user)):
    """API endpoint to get all users"""
    users = get_all_users()
    return {"users": [user.dict() for user in users]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
