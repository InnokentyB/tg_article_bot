"""
Authentication and authorization system for the API
"""
import os
import time
import jwt
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
API_KEY = os.getenv("API_KEY")

# Rate limiting
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 100  # requests per window

# In-memory storage for rate limiting (in production use Redis)
rate_limit_store: Dict[str, Dict[str, Any]] = {}

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    hashed_password: Optional[str] = None
    role: str = "user"  # "user" or "admin"

def _load_users_from_env() -> Dict[str, Dict[str, Any]]:
    """Load web-admin users from environment variables."""
    users: Dict[str, Dict[str, Any]] = {}

    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_username and admin_password:
        users[admin_username] = {
            "username": admin_username,
            "full_name": os.getenv("ADMIN_FULL_NAME", "Administrator"),
            "email": os.getenv("ADMIN_EMAIL", ""),
            "hashed_password": admin_password,
            "disabled": False,
            "role": "admin",
        }

    user_username = os.getenv("WEB_USER_USERNAME")
    user_password = os.getenv("WEB_USER_PASSWORD")
    if user_username and user_password:
        users[user_username] = {
            "username": user_username,
            "full_name": os.getenv("WEB_USER_FULL_NAME", "User"),
            "email": os.getenv("WEB_USER_EMAIL", ""),
            "hashed_password": user_password,
            "disabled": False,
            "role": "user",
        }

    return users


# In production, replace this with persistent users and hashed passwords.
fake_users_db = _load_users_from_env()

security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password without leaking timing information."""
    return hmac.compare_digest(plain_password or "", hashed_password or "")

def get_user(username: str) -> Optional[User]:
    """Get user from database"""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(**user_dict)
    return None

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    if not fake_users_db:
        logger.error("No web-admin users configured. Set ADMIN_USERNAME and ADMIN_PASSWORD.")
        return None
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY environment variable is required")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key from Bearer token"""
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured",
        )
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

async def get_current_user(token: str = Depends(security)):
    """Get current user from JWT token"""
    if not SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT authentication is not configured",
        )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Get current active user"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    """Get current admin user"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Admin access required"
        )
    return current_user

def check_rate_limit(request: Request):
    """Check rate limit for the request"""
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old entries
    if client_ip in rate_limit_store:
        old_requests = rate_limit_store[client_ip]["requests"]
        rate_limit_store[client_ip]["requests"] = [
            req_time for req_time in old_requests 
            if current_time - req_time < RATE_LIMIT_WINDOW
        ]
    else:
        rate_limit_store[client_ip] = {"requests": []}
    
    # Check if limit exceeded
    if len(rate_limit_store[client_ip]["requests"]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    
    # Add current request
    rate_limit_store[client_ip]["requests"].append(current_time)

async def rate_limit_middleware(request: Request):
    """Rate limiting middleware"""
    check_rate_limit(request)

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username from fake database"""
    if username in fake_users_db:
        return fake_users_db[username]
    return None

def get_all_users() -> list:
    """Get all users from fake database"""
    return list(fake_users_db.values())
