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

    async def ensure_vector_index(self, dimensions: int) -> None:
        """Create an IVFFLAT cosine-distance index on article_embeddings.embedding.

        pgvector requires the column to be cast to ``vector(N)`` with a fixed
        dimension before an approximate-nearest-neighbour index can be built.
        This method is idempotent — it skips creation if the index already exists.

        Args:
            dimensions: Embedding dimension (e.g. 32 for fake, 1536 for OpenAI).
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        index_name = f"idx_article_embeddings_ivfflat_{dimensions}"
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_indexes WHERE indexname = $1",
                index_name,
            )
            if exists:
                return
            try:
                await conn.execute(
                    f"""
                    CREATE INDEX {index_name}
                        ON article_embeddings
                        USING ivfflat ((embedding::vector({dimensions})) vector_cosine_ops)
                        WITH (lists = 100)
                    """
                )
                logger.info(
                    "Created IVFFLAT vector index %s (dimensions=%d)", index_name, dimensions
                )
            except Exception as exc:
                # Non-fatal: sequential scan will be used instead.
                logger.warning("Could not create IVFFLAT index: %s", exc)

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
        fetch_interval_hours: int = 2,
    ) -> int:
        """Create or update a content source."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            if url:
                return await conn.fetchval(
                    """INSERT INTO sources (name, url, source_type, language, metadata, fetch_interval_hours)
                       VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                       ON CONFLICT (url) DO UPDATE SET
                           name = EXCLUDED.name,
                           source_type = EXCLUDED.source_type,
                           language = COALESCE(EXCLUDED.language, sources.language),
                           metadata = sources.metadata || EXCLUDED.metadata,
                           fetch_interval_hours = EXCLUDED.fetch_interval_hours,
                           updated_at = CURRENT_TIMESTAMP
                       RETURNING id""",
                    name,
                    url,
                    source_type,
                    language,
                    json.dumps(metadata or {}),
                    fetch_interval_hours,
                )

            return await conn.fetchval(
                """INSERT INTO sources (name, source_type, language, metadata, fetch_interval_hours)
                   VALUES ($1, $2, $3, $4::jsonb, $5)
                   RETURNING id""",
                name,
                source_type,
                language,
                json.dumps(metadata or {}),
                fetch_interval_hours,
            )

    async def get_sources(
        self,
        active_only: bool = True,
        due_for_fetch: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return content sources from the database.

        Args:
            active_only: When True (default) only active sources are returned.
            due_for_fetch: When True only sources whose next scheduled crawl has
                arrived are returned. Requires active_only=True to be meaningful.
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            query = """
                SELECT
                    id, name, url, source_type, language, is_active,
                    fetch_interval_hours, last_fetched_at, metadata,
                    created_at, updated_at
                FROM sources
                WHERE TRUE
            """
            conditions = []
            if active_only:
                conditions.append("is_active = TRUE")
            if due_for_fetch:
                conditions.append(
                    "(last_fetched_at IS NULL OR "
                    "last_fetched_at < NOW() - fetch_interval_hours * INTERVAL '1 hour')"
                )
            if conditions:
                query += " AND " + " AND ".join(conditions)
            query += " ORDER BY last_fetched_at ASC NULLS FIRST, id ASC"

            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    async def update_source_last_fetched(self, source_id: int) -> None:
        """Atomically update last_fetched_at to the current timestamp for a source.

        Args:
            source_id: Primary key of the source to update.
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE sources SET last_fetched_at = NOW(), updated_at = NOW() WHERE id = $1",
                source_id,
            )
        logger.info("Updated last_fetched_at for source_id=%d", source_id)

    async def delete_source(self, source_id: int) -> bool:
        """Soft-delete a source by setting is_active = FALSE.

        Returns:
            True if the source was found and deactivated, False otherwise.
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE sources SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
                source_id,
            )
        affected = int(result.split()[-1])
        if affected:
            logger.info("Soft-deleted source_id=%d (is_active set to FALSE)", source_id)
        return bool(affected)

    async def is_email_processed(self, message_id: str) -> bool:
        """Check if an email message has already been processed."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM processed_emails WHERE message_id = $1)",
                message_id,
            )
            return bool(exists)

    async def mark_email_processed(self, message_id: str, subject: str, sender: str) -> None:
        """Mark an email message as processed to prevent double spending/parsing."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO processed_emails (message_id, subject, sender)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (message_id) DO NOTHING""",
                message_id,
                subject,
                sender,
            )
        logger.info("Marked email message_id=%s as processed", message_id)

    async def get_email_filters(self) -> List[str]:
        """Fetch all blocked link patterns/domains."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT pattern FROM email_filters WHERE is_blocked = TRUE")
            return [row["pattern"] for row in rows]

    async def add_email_filter(self, pattern: str) -> None:
        """Dynamically add a new pattern to the links block list."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO email_filters (pattern, is_blocked)
                   VALUES ($1, TRUE)
                   ON CONFLICT (pattern) DO UPDATE SET is_blocked = TRUE, created_at = NOW()""",
                pattern.strip().lower(),
            )
        logger.info("Added email link filter pattern: %s", pattern)



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
        
        # Convert List[float] to pgvector-compatible string (e.g. "[0.1, 0.2, 0.3]")
        embedding_str = f"[{','.join(map(str, embedding))}]"
        
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """INSERT INTO article_embeddings
                   (article_id, chunk_id, model, embedding, embedding_dimensions)
                   VALUES ($1, $2, $3, $4::vector, $5)
                   ON CONFLICT (chunk_id, model) DO UPDATE SET
                       embedding = EXCLUDED.embedding,
                       embedding_dimensions = EXCLUDED.embedding_dimensions,
                       created_at = CURRENT_TIMESTAMP
                   RETURNING id""",
                article_id,
                chunk_id,
                model,
                embedding_str,
                len(embedding),
            )

    async def vector_search(
        self,
        query_vector: List[float],
        model: str,
        max_results: int = 20,
        language: Optional[str] = None,
        period_days: Optional[int] = None,
    ) -> List[Dict]:
        """Search article chunks by cosine similarity using pgvector SQL operators.

        Uses the ``<=>`` operator (cosine distance) so ranking is done entirely
        inside Postgres — no Python-side matrix math required.  Returns the
        best-scoring chunk per article, sorted by similarity descending.

        Args:
            query_vector: Embedding of the search query (must match stored dimension).
            model:        Embedding model name to filter by.
            max_results:  Maximum number of *articles* to return.
            language:     Optional ISO-639-1 language filter.
            period_days:  Optional recency filter (days since published/created).

        Returns:
            List of dicts with keys: article_id, title, summary, source, author,
            original_link, canonical_url, language, published_at, created_at,
            chunk_id, chunk_index, chunk_text, score.
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        # Convert List[float] query_vector to pgvector string format (e.g. "[0.1, 0.2, 0.3]")
        query_vector_str = f"[{','.join(map(str, query_vector))}]"

        query = """
            SELECT DISTINCT ON (a.id)
                a.id          AS article_id,
                a.title,
                a.summary,
                a.source,
                a.author,
                a.original_link,
                a.canonical_url,
                a.language,
                a.published_at,
                a.created_at,
                c.id          AS chunk_id,
                c.chunk_index,
                c.text        AS chunk_text,
                1 - (e.embedding <=> $1::vector) AS score
            FROM article_embeddings e
            JOIN article_chunks c ON c.id = e.chunk_id
            JOIN articles     a ON a.id = e.article_id
            WHERE e.model = $2
        """
        params: List[Any] = [query_vector_str, model]
        param_count = 3

        if language:
            query += f" AND a.language = ${param_count}"
            params.append(language)
            param_count += 1

        if period_days:
            query += (
                f" AND COALESCE(a.published_at, a.created_at)"
                f" >= NOW() - (${param_count} * INTERVAL '1 day')"
            )
            params.append(period_days)
            param_count += 1

        # ORDER BY must include the DISTINCT ON column first, then the sort key.
        query += f"""
            ORDER BY a.id,
                     e.embedding <=> $1::vector
            LIMIT ${param_count}
        """
        params.append(max_results)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = [dict(row) for row in rows]
            # Re-sort by score DESC after DISTINCT ON (Postgres returns them by a.id).
            results.sort(key=lambda r: r["score"] or 0.0, reverse=True)
            logger.info(
                "pgvector search returned %d results for model=%s",
                len(results),
                model,
            )
            return results

    async def get_embedding_rows_for_search(
        self,
        model: str,
        language: Optional[str] = None,
        period_days: Optional[int] = None,
        limit: int = 1000,
    ) -> List[Dict]:
        """Load chunk embeddings for Python-side similarity search.

        .. deprecated::
            Use :meth:`vector_search` instead.  This method fetches raw
            embedding arrays into Python memory and computes cosine similarity
            there, which does not scale.  It is retained as a fallback for
            environments where pgvector is unavailable.
        """
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
                e.embedding::text AS embedding,
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
            results = []
            for row in rows:
                row_dict = dict(row)
                if isinstance(row_dict.get("embedding"), str):
                    # Parse '[0.123,0.456,...]' string representation into list of floats
                    row_dict["embedding"] = [
                        float(val)
                        for val in row_dict["embedding"].strip("[]").split(",")
                        if val
                    ]
                results.append(row_dict)
            return results

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
