"""
Database manager for article processing system
"""
import asyncpg
import hashlib
import json
import logging
from typing import Any, List, Dict, Optional, Tuple
import os
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

    async def upsert_source(
        self,
        name: str,
        url: Optional[str] = None,
        source_type: str = "web",
        language: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create or update a content source."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            if url:
                return await conn.fetchval(
                    """INSERT INTO sources (name, url, source_type, language, metadata)
                       VALUES ($1, $2, $3, $4, $5::jsonb)
                       ON CONFLICT (url) DO UPDATE SET
                           name = EXCLUDED.name,
                           source_type = EXCLUDED.source_type,
                           language = COALESCE(EXCLUDED.language, sources.language),
                           metadata = sources.metadata || EXCLUDED.metadata,
                           updated_at = CURRENT_TIMESTAMP
                       RETURNING id""",
                    name,
                    url,
                    source_type,
                    language,
                    json.dumps(metadata or {}),
                )

            return await conn.fetchval(
                """INSERT INTO sources (name, source_type, language, metadata)
                   VALUES ($1, $2, $3, $4::jsonb)
                   RETURNING id""",
                name,
                source_type,
                language,
                json.dumps(metadata or {}),
            )

    async def update_article_intelligence_fields(
        self,
        article_id: int,
        source_id: Optional[int] = None,
        canonical_url: Optional[str] = None,
        published_at: Optional[datetime] = None,
        extracted_at: Optional[datetime] = None,
        popularity_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update MVP article-intelligence metadata for an existing article."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE articles SET
                       source_id = COALESCE($2, source_id),
                       canonical_url = COALESCE($3, canonical_url),
                       published_at = COALESCE($4, published_at),
                       extracted_at = COALESCE($5, extracted_at),
                       popularity_score = COALESCE($6, popularity_score),
                       metadata = metadata || $7::jsonb,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = $1""",
                article_id,
                source_id,
                canonical_url,
                published_at,
                extracted_at,
                popularity_score,
                json.dumps(metadata or {}),
            )

    async def replace_article_chunks(self, article_id: int, chunks: List[Dict[str, Any]]) -> List[Dict]:
        """Replace all chunks for an article and return inserted rows."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM article_chunks WHERE article_id = $1", article_id)
                inserted = []
                for index, chunk in enumerate(chunks):
                    row = await conn.fetchrow(
                        """INSERT INTO article_chunks
                           (article_id, chunk_index, text, token_count, metadata)
                           VALUES ($1, $2, $3, $4, $5::jsonb)
                           RETURNING *""",
                        article_id,
                        chunk.get("chunk_index", index),
                        chunk["text"],
                        chunk.get("token_count"),
                        json.dumps(chunk.get("metadata") or {}),
                    )
                    inserted.append(dict(row))
                return inserted

    async def get_article_chunks(self, article_id: int) -> List[Dict]:
        """Get chunks for an article ordered by chunk index."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT *
                   FROM article_chunks
                   WHERE article_id = $1
                   ORDER BY chunk_index ASC""",
                article_id,
            )
            return [dict(row) for row in rows]

    async def upsert_article_embedding(
        self,
        article_id: int,
        chunk_id: int,
        model: str,
        embedding: List[float],
    ) -> int:
        """Create or update an embedding for a chunk."""
        if not embedding:
            raise ValueError("Embedding must not be empty")
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """INSERT INTO article_embeddings
                   (article_id, chunk_id, model, embedding, embedding_dimensions)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (chunk_id, model) DO UPDATE SET
                       embedding = EXCLUDED.embedding,
                       embedding_dimensions = EXCLUDED.embedding_dimensions,
                       created_at = CURRENT_TIMESTAMP
                   RETURNING id""",
                article_id,
                chunk_id,
                model,
                embedding,
                len(embedding),
            )

    async def get_embedding_rows_for_search(
        self,
        model: str,
        language: Optional[str] = None,
        period_days: Optional[int] = None,
        limit: int = 1000,
    ) -> List[Dict]:
        """Load chunk embeddings for MVP Python-side similarity search."""
        query = """
            SELECT
                a.id AS article_id,
                a.title,
                a.summary,
                a.source,
                a.author,
                a.original_link,
                a.canonical_url,
                a.language,
                a.published_at,
                a.created_at,
                c.id AS chunk_id,
                c.chunk_index,
                c.text AS chunk_text,
                e.embedding,
                e.model
            FROM article_embeddings e
            JOIN article_chunks c ON c.id = e.chunk_id
            JOIN articles a ON a.id = e.article_id
            WHERE e.model = $1
        """
        params: List[Any] = [model]
        param_count = 2

        if language:
            query += f" AND a.language = ${param_count}"
            params.append(language)
            param_count += 1

        if period_days:
            query += f" AND COALESCE(a.published_at, a.created_at) >= NOW() - (${param_count} * INTERVAL '1 day')"
            params.append(period_days)
            param_count += 1

        query += f" ORDER BY COALESCE(a.published_at, a.created_at) DESC LIMIT ${param_count}"
        params.append(limit)

        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def create_topic_query(
        self,
        topic: str,
        language: Optional[str] = None,
        period_days: Optional[int] = None,
        max_sources: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Store an editorial topic query."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """INSERT INTO topic_queries
                   (topic, language, period_days, max_sources, metadata)
                   VALUES ($1, $2, $3, $4, $5::jsonb)
                   RETURNING id""",
                topic,
                language,
                period_days,
                max_sources,
                json.dumps(metadata or {}),
            )

    async def create_review(
        self,
        topic_query_id: Optional[int],
        title: Optional[str],
        review_markdown: str,
        telegram_draft: str,
        selected_sources: Optional[List[Dict[str, Any]]] = None,
        status: str = "draft",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Store a generated review and the articles selected for it."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                review_id = await conn.fetchval(
                    """INSERT INTO reviews
                       (topic_query_id, title, review_markdown, telegram_draft, status, metadata)
                       VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                       RETURNING id""",
                    topic_query_id,
                    title,
                    review_markdown,
                    telegram_draft,
                    status,
                    json.dumps(metadata or {}),
                )

                for index, source in enumerate(selected_sources or [], start=1):
                    await conn.execute(
                        """INSERT INTO review_sources
                           (review_id, article_id, rank, selection_reason, relevance_score, critique_summary)
                           VALUES ($1, $2, $3, $4, $5, $6)
                           ON CONFLICT (review_id, article_id) DO UPDATE SET
                               rank = EXCLUDED.rank,
                               selection_reason = EXCLUDED.selection_reason,
                               relevance_score = EXCLUDED.relevance_score,
                               critique_summary = EXCLUDED.critique_summary""",
                        review_id,
                        source["article_id"],
                        source.get("rank", index),
                        source.get("selection_reason"),
                        source.get("relevance_score"),
                        source.get("critique_summary"),
                    )

                return review_id
