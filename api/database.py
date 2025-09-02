"""
Database manager for article processing system
"""
import asyncpg
import hashlib
import json
import logging
from typing import List, Dict, Optional, Tuple
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.pool = None
        self.db_url = os.getenv('DATABASE_URL')
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(self.db_url)
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
    
    def generate_fingerprint(self, text: str) -> str:
        """Generate unique fingerprint for article text"""
        # Normalize text: remove extra whitespace, convert to lowercase
        normalized_text = ' '.join(text.lower().split())
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
    
    async def save_user(self, telegram_user_id: int, username: Optional[str] = None, 
                       first_name: Optional[str] = None, last_name: Optional[str] = None) -> int:
        """Save or update user information"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            # Check if user exists
            existing_user = await conn.fetchrow(
                "SELECT id FROM users WHERE telegram_user_id = $1",
                telegram_user_id
            )
            
            if existing_user:
                # Update existing user
                await conn.execute(
                    """UPDATE users 
                       SET username = $2, first_name = $3, last_name = $4, updated_at = CURRENT_TIMESTAMP
                       WHERE telegram_user_id = $1""",
                    telegram_user_id, username, first_name, last_name
                )
                return existing_user['id']
            else:
                # Create new user
                user_id = await conn.fetchval(
                    """INSERT INTO users (telegram_user_id, username, first_name, last_name)
                       VALUES ($1, $2, $3, $4) RETURNING id""",
                    telegram_user_id, username, first_name, last_name
                )
                return user_id
    
    async def check_duplicate(self, fingerprint: str) -> Optional[Dict]:
        """Check if article with given fingerprint already exists"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            article = await conn.fetchrow(
                """SELECT id, title, summary, source, author, original_link, 
                          categories_user, categories_auto, created_at, telegram_user_id
                   FROM articles WHERE fingerprint = $1""",
                fingerprint
            )
            
            if article:
                return dict(article)
            return None
    
    async def save_article(self, title: Optional[str] = None, text: Optional[str] = None, summary: Optional[str] = None,
                          source: Optional[str] = None, author: Optional[str] = None, is_translated: bool = False,
                          original_link: Optional[str] = None, categories_user: Optional[List[str]] = None,
                          categories_advanced: Optional[Dict] = None, language: Optional[str] = None, 
                          telegram_user_id: Optional[int] = None) -> Tuple[Optional[int], str]:
        """Save new article to database"""
        if not text:
            raise ValueError("Article text is required")
        
        fingerprint = self.generate_fingerprint(text)
        
        # Check for duplicates first
        duplicate = await self.check_duplicate(fingerprint)
        if duplicate:
            return None, fingerprint
        
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            article_id = await conn.fetchval(
                """INSERT INTO articles 
                   (title, text, summary, fingerprint, source, author, is_translated, 
                    original_link, categories_user, categories_advanced, language, telegram_user_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) 
                   RETURNING id""",
                title, text, summary, fingerprint, source, author, is_translated,
                original_link, categories_user or [], json.dumps(categories_advanced) if categories_advanced else None, language, telegram_user_id
            )
            
            logger.info(f"Saved article {article_id} with fingerprint {fingerprint[:8]}...")
            return article_id, fingerprint
    
    async def update_article_categories(self, article_id: int, categories_auto: List[str]):
        """Update automatic categories for an article"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE articles SET categories_auto = $2, updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                article_id, categories_auto
            )
    
    async def update_counters(self, article_id: int, comments_count: Optional[int] = None,
                             likes_count: Optional[int] = None, views_count: Optional[int] = None):
        """Update article counters"""
        updates = []
        params = [article_id]
        param_count = 2
        
        if comments_count is not None:
            updates.append(f"comments_count = ${param_count}")
            params.append(comments_count)
            param_count += 1
            
        if likes_count is not None:
            updates.append(f"likes_count = ${param_count}")
            params.append(likes_count)
            param_count += 1
            
        if views_count is not None:
            updates.append(f"views_count = ${param_count}")
            params.append(views_count)
            param_count += 1
        
        if updates:
            query = f"UPDATE articles SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = $1"
            if not self.pool:
                raise RuntimeError("Database pool not initialized")
            async with self.pool.acquire() as conn:
                await conn.execute(query, *params)
    
    async def get_articles(self, limit: int = 50, offset: int = 0,
                          category: Optional[str] = None, user_id: Optional[int] = None,
                          search_text: Optional[str] = None) -> List[Dict]:
        """Get articles with filtering options"""
        query = """
            SELECT id, title, summary, source, author, original_link,
                   categories_user, categories_auto, categories_advanced, language, 
                   comments_count, likes_count, views_count,
                   telegram_user_id, created_at, updated_at
            FROM articles
            WHERE 1=1
        """
        params = []
        param_count = 1
        
        if category:
            query += f" AND ($1 = ANY(categories_user) OR $1 = ANY(categories_auto))"
            params.append(category)
            param_count += 1
        
        if user_id:
            query += f" AND telegram_user_id = ${param_count}"
            params.append(user_id)
            param_count += 1
        
        if search_text:
            query += f" AND (title ILIKE ${param_count} OR text ILIKE ${param_count})"
            params.append(f"%{search_text}%")
            param_count += 1
        
        query += f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])
        
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def get_article_by_id(self, article_id: int) -> Optional[Dict]:
        """Get article by ID"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            article = await conn.fetchrow(
                """SELECT * FROM articles WHERE id = $1""",
                article_id
            )
            return dict(article) if article else None
    
    async def get_article_by_fingerprint(self, fingerprint: str) -> Optional[Dict]:
        """Get article by fingerprint"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            article = await conn.fetchrow(
                """SELECT * FROM articles WHERE fingerprint = $1""",
                fingerprint
            )
            return dict(article) if article else None