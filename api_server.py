#!/usr/bin/env python3
"""
API Server для Railway (простая версия)
"""
import os
import logging
import re
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
from html import unescape
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
db_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    global db_manager
    
    # Startup
    logger.info("Starting up API server...")
    
    # Log environment variables
    logger.info(f"PORT: {os.getenv('PORT', 'not set')}")
    logger.info(f"DATABASE_URL: {'set' if os.getenv('DATABASE_URL') else 'not set'}")
    logger.info(f"RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'not set')}")
    logger.info(f"API_KEY: {'set' if os.getenv('API_KEY') else 'not set'}")
    
    # Try to initialize database
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Apply the canonical schema used by local development and MVP endpoints.
        try:
            schema_path = os.getenv("DATABASE_SCHEMA_PATH", "init.sql")
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as schema_file:
                    schema_sql = schema_file.read()
                async with db_manager.pool.acquire() as conn:
                    await conn.execute(schema_sql)
                logger.info("✅ Database schema applied successfully")
            else:
                logger.warning(f"⚠️ Database schema file not found: {schema_path}")
        except Exception as schema_error:
            logger.error(f"❌ Database schema application failed: {schema_error}")
            raise
        
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization failed: {e}")
        db_manager = None
    
    yield
    
    # Shutdown
    logger.info("Shutting down API server...")
    if db_manager:
        await db_manager.close()
        logger.info("Database connection closed")

# Create FastAPI app
app = FastAPI(
    title="Railway API",
    description="API for Railway deployment with n8n integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key from Authorization header"""
    api_key = os.getenv('API_KEY')
    
    if not api_key:
        logger.error("API_KEY is not configured")
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured"
        )
    
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if it's a Bearer token
    if not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=401, 
            detail="Invalid authorization format. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract token
    token = authorization.replace('Bearer ', '')
    
    if token != api_key:
        raise HTTPException(
            status_code=403, 
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return True



@app.get("/")
async def read_root():
    """Root endpoint"""
    logger.info("Root endpoint called")
    return {
        "message": "Railway API is running!", 
        "status": "ok"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check called")
    return {
        "status": "healthy", 
        "service": "railway-api"
    }

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint for Railway"""
    logger.info("API health check called")
    return {
        "status": "healthy", 
        "service": "railway-api"
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint"""
    global db_manager
    
    logger.info("Test endpoint called")
    
    db_status = "connected" if db_manager else "not connected"
    
    return {
        "message": "Test endpoint works!",
        "port": os.getenv("PORT", "not set"),
        "database_url": "set" if os.getenv("DATABASE_URL") else "not set",
        "railway_environment": os.getenv("RAILWAY_ENVIRONMENT", "not set"),
        "database_status": db_status
    }

@app.get("/articles")
async def get_articles(limit: int = 10, offset: int = 0):
    """Get articles"""
    global db_manager
    
    try:
        if db_manager:
            # Use global database manager
            articles = await db_manager.get_articles(limit=limit, offset=offset)
            return {"articles": articles, "count": len(articles)}
        else:
            # Fallback to mock data
            logger.warning("Database not available, using mock data")
            return {
                "articles": [
                    {
                        "id": 1,
                        "title": "Mock Article",
                        "text": "This is a mock article",
                        "categories": ["Technology"],
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                ],
                "count": 1
            }
        
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        return {"error": str(e)}

@app.get("/statistics")
async def get_statistics():
    """Get statistics"""
    try:
        global db_manager
        
        if db_manager:
            try:
                async with db_manager.pool.acquire() as conn:
                    articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
                    users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                
                return {
                    "articles_count": articles_count,
                    "users_count": users_count,
                    "ml_service": "basic",
                    "database": "enabled",
                    "status": "ok"
                }
                
            except Exception as db_error:
                logger.warning(f"Database error, using mock data: {db_error}")
                # Fallback to mock data
                return {
                    "articles_count": 1,
                    "users_count": 1,
                    "ml_service": "basic",
                    "database": "disabled",
                    "status": "ok"
                }
        else:
            # Database not available, use mock data
            logger.warning("Database not available, using mock data")
            return {
                "articles_count": 1,
                "users_count": 1,
                "ml_service": "basic",
                "database": "disabled",
                "status": "ok"
            }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"error": str(e)}

@app.get("/debug/database")
async def debug_database():
    """Debug database connection and tables"""
    global db_manager
    
    try:
        if not db_manager:
            return {
                "status": "error",
                "message": "Database manager not initialized",
                "database_url": "set" if os.getenv("DATABASE_URL") else "not set"
            }
        
        # Test database connection
        async with db_manager.pool.acquire() as conn:
            # Check tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            existing_tables = [row['table_name'] for row in tables]
            
            # Get counts
            users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
            
            return {
                "status": "connected",
                "tables": existing_tables,
                "users_count": users_count,
                "articles_count": articles_count,
                "database_url": "set" if os.getenv("DATABASE_URL") else "not set"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "database_url": "set" if os.getenv("DATABASE_URL") else "not set"
        }

@app.post("/ingest/url")
async def ingest_url(article_data: dict, auth: bool = Depends(verify_api_key)):
    """Ingest an article from a URL into the MVP article intelligence store."""
    return await ingest_url_payload(article_data)

async def ingest_url_payload(article_data: dict) -> dict:
    """Shared URL ingestion logic for direct URL and RSS ingestion."""
    global db_manager

    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    url = (article_data.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    language = article_data.get("language")
    source_name = article_data.get("source_name")

    from text_extractor import TextExtractor

    text_extractor = TextExtractor()
    await text_extractor.initialize()
    try:
        extracted = await text_extractor.extract_from_url(url)
    finally:
        await text_extractor.close()

    fallback_text = normalize_feed_text(article_data.get("fallback_text"))
    if (not extracted or not extracted.get("text")) and not fallback_text:
        raise HTTPException(status_code=400, detail="Failed to extract article text from URL")

    parsed_url = urlparse(url)
    extracted = extracted or {}
    source_url = extracted.get("source") or f"{parsed_url.scheme}://{parsed_url.netloc}"
    source_name = source_name or parsed_url.netloc or source_url
    text = extracted.get("text") or fallback_text
    title = extracted.get("title") or article_data.get("title")
    summary = normalize_feed_text(article_data.get("summary")) or text_extractor.generate_summary(text)
    categories = await basic_categorize(text)

    try:
        source_id = await db_manager.upsert_source(
            name=source_name,
            url=source_url,
            source_type=article_data.get("source_type", "web"),
            language=language,
            metadata={"ingested_from": "url"},
        )

        article_id, fingerprint = await db_manager.save_article(
            title=title,
            text=text,
            summary=summary,
            source=source_url,
            author=extracted.get("author"),
            original_link=url,
            categories_user=categories,
            language=language,
            telegram_user_id=article_data.get("telegram_user_id"),
        )

        if article_id is None:
            duplicate = await db_manager.get_article_by_fingerprint(fingerprint)
            return {
                "status": "duplicate",
                "article_id": duplicate.get("id") if duplicate else None,
                "fingerprint": fingerprint,
                "source_id": source_id,
            }

        await db_manager.update_article_intelligence_fields(
            article_id=article_id,
            source_id=source_id,
            canonical_url=url,
            extracted_at=datetime.now(),
            metadata={
                "keywords": extracted.get("keywords") or [],
                "ingestion_method": article_data.get("ingestion_method", "url"),
                "extraction_fallback": bool(fallback_text and not extracted.get("text")),
            },
        )
        await db_manager.update_article_categories(article_id, categories)

        from article_chunker import ArticleChunker

        chunks = ArticleChunker().chunk_text(text)
        inserted_chunks = await db_manager.replace_article_chunks(article_id, chunks)

        return {
            "status": "created",
            "article_id": article_id,
            "source_id": source_id,
            "fingerprint": fingerprint,
            "title": title,
            "text_length": len(text),
            "chunks_count": len(inserted_chunks),
            "categories": categories,
        }

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"URL ingestion failed for {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def normalize_feed_text(value: Optional[str]) -> Optional[str]:
    """Convert RSS summary/content HTML into plain text for ingestion fallback."""
    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None

@app.post("/ingest/rss")
async def ingest_rss(feed_data: dict, auth: bool = Depends(verify_api_key)):
    """Ingest articles from an RSS/Atom feed."""
    global db_manager

    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    feed_url = (feed_data.get("feed_url") or "").strip()
    if not feed_url:
        raise HTTPException(status_code=400, detail="feed_url is required")

    limit = int(feed_data.get("limit") or 20)
    limit = max(1, min(limit, 100))
    language = feed_data.get("language")
    source_name = feed_data.get("source_name")

    try:
        import feedparser
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="feedparser package is not installed") from exc

    parsed_feed = feedparser.parse(feed_url)
    if parsed_feed.bozo and not parsed_feed.entries:
        raise HTTPException(status_code=400, detail=f"Failed to parse feed: {parsed_feed.bozo_exception}")

    resolved_source_name = source_name or parsed_feed.feed.get("title") or feed_url
    source_id = await db_manager.upsert_source(
        name=resolved_source_name,
        url=feed_url,
        source_type="rss",
        language=language,
        metadata={
            "feed_title": parsed_feed.feed.get("title"),
            "feed_link": parsed_feed.feed.get("link"),
        },
    )

    results = []
    for entry in parsed_feed.entries[:limit]:
        entry_url = entry.get("link")
        if not entry_url:
            results.append(
                {
                    "status": "failed",
                    "title": entry.get("title"),
                    "error": "Entry has no link",
                }
            )
            continue

        try:
            fallback_parts = [
                entry.get("title"),
                entry.get("summary"),
                entry.get("description"),
            ]
            for content_item in entry.get("content", []) or []:
                fallback_parts.append(content_item.get("value"))
            fallback_text = "\n\n".join(
                part for part in (normalize_feed_text(part) for part in fallback_parts) if part
            )

            result = await ingest_url_payload(
                {
                    "url": entry_url,
                    "title": entry.get("title"),
                    "source_name": resolved_source_name,
                    "source_type": "rss_entry",
                    "language": language,
                    "summary": entry.get("summary"),
                    "fallback_text": fallback_text,
                    "ingestion_method": "rss",
                }
            )
            result["feed_entry_title"] = entry.get("title")
            results.append(result)
        except HTTPException as exc:
            results.append(
                {
                    "status": "failed",
                    "url": entry_url,
                    "title": entry.get("title"),
                    "error": exc.detail,
                }
            )
        except Exception as exc:
            logger.error(f"RSS entry ingestion failed for {entry_url}: {exc}")
            results.append(
                {
                    "status": "failed",
                    "url": entry_url,
                    "title": entry.get("title"),
                    "error": str(exc),
                }
            )

    summary = {
        "created": sum(1 for item in results if item.get("status") == "created"),
        "duplicates": sum(1 for item in results if item.get("status") == "duplicate"),
        "failed": sum(1 for item in results if item.get("status") == "failed"),
    }

    return {
        "status": "completed",
        "source_id": source_id,
        "feed_url": feed_url,
        "source_name": resolved_source_name,
        "limit": limit,
        "summary": summary,
        "results": results,
    }

@app.post("/embeddings/rebuild")
async def rebuild_embeddings(request_data: dict, auth: bool = Depends(verify_api_key)):
    """Rebuild chunk embeddings for an article."""
    global db_manager

    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    article_id = request_data.get("article_id")
    if not article_id:
        raise HTTPException(status_code=400, detail="article_id is required")

    article = await db_manager.get_article_by_id(int(article_id))
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    chunks = await db_manager.get_article_chunks(int(article_id))
    if not chunks:
        from article_chunker import ArticleChunker

        chunk_payloads = ArticleChunker().chunk_text(article.get("text") or "")
        if not chunk_payloads:
            raise HTTPException(status_code=400, detail="Article has no text to embed")
        chunks = await db_manager.replace_article_chunks(int(article_id), chunk_payloads)

    from embedding_provider import get_embedding_provider

    provider = get_embedding_provider()
    texts = [chunk["text"] for chunk in chunks]
    vectors = await provider.embed_texts(texts)

    if len(vectors) != len(chunks):
        raise HTTPException(status_code=500, detail="Embedding provider returned mismatched vector count")

    embedding_ids = []
    for chunk, vector in zip(chunks, vectors):
        embedding_id = await db_manager.upsert_article_embedding(
            article_id=int(article_id),
            chunk_id=chunk["id"],
            model=request_data.get("model") or provider.model,
            embedding=vector,
        )
        embedding_ids.append(embedding_id)

    # Idempotently ensure the vector index exists for these dimensions
    if vectors and len(vectors[0]) > 0:
        await db_manager.ensure_vector_index(len(vectors[0]))

    return {
        "status": "rebuilt",
        "article_id": int(article_id),
        "model": request_data.get("model") or provider.model,
        "chunks_count": len(chunks),
        "embeddings_count": len(embedding_ids),
        "embedding_dimensions": len(vectors[0]) if vectors else 0,
    }


async def build_topic_search_results(request_data: dict) -> dict:
    """Search relevant articles for an editorial topic.

    Attempts a pgvector SQL cosine-similarity search first (``vector_search``).
    If pgvector operators are unavailable in the current Postgres instance it
    transparently falls back to fetching all embeddings and computing cosine
    similarity in Python.
    """
    global db_manager

    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    topic = (request_data.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")

    max_sources = int(request_data.get("max_sources") or 5)
    language = request_data.get("language")
    period_days = request_data.get("period_days")

    from embedding_provider import get_embedding_provider

    provider = get_embedding_provider()
    query_vector = (await provider.embed_texts([topic]))[0]
    model = request_data.get("model") or provider.model

    # --- Primary path: pgvector SQL search ---
    try:
        rows = await db_manager.vector_search(
            query_vector=query_vector,
            model=model,
            max_results=max_sources,
            language=language,
            period_days=period_days,
        )
        if rows:
            results = [
                {
                    "article_id": row["article_id"],
                    "title": row.get("title"),
                    "summary": row.get("summary"),
                    "source": row.get("source"),
                    "author": row.get("author"),
                    "original_link": row.get("original_link"),
                    "canonical_url": row.get("canonical_url"),
                    "language": row.get("language"),
                    "published_at": row.get("published_at"),
                    "created_at": row.get("created_at"),
                    "best_chunk_id": row.get("chunk_id"),
                    "best_chunk_index": row.get("chunk_index"),
                    "best_chunk_preview": (row.get("chunk_text") or "")[:500],
                    "score": row["score"],
                    "selection_reason": "Selected by pgvector cosine similarity to the requested topic.",
                }
                for row in rows
            ]
            topic_query_id = await db_manager.create_topic_query(
                topic=topic,
                language=language,
                period_days=period_days,
                max_sources=max_sources,
                metadata={"model": model, "mode": "embedding_similarity"},
            )
            return {
                "topic_query_id": topic_query_id,
                "topic": topic,
                "mode": "embedding_similarity",
                "model": model,
                "results": results,
            }
    except Exception as pgvector_err:
        logger.warning(
            "pgvector search failed (%s: %s), falling back to Python-side similarity.",
            type(pgvector_err).__name__,
            pgvector_err,
        )

    # --- Fallback path: Python cosine similarity ---
    import math

    def _cosine(left: list, right: list) -> float:
        """Local fallback cosine similarity (Python-side, no pgvector)."""
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        ln = math.sqrt(sum(a * a for a in left)) or 1.0
        rn = math.sqrt(sum(b * b for b in right)) or 1.0
        return dot / (ln * rn)

    legacy_rows = await db_manager.get_embedding_rows_for_search(
        model=model,
        language=language,
        period_days=period_days,
        limit=int(request_data.get("candidate_limit") or 1000),
    )

    if not legacy_rows:
        articles = await db_manager.get_articles(
            limit=max_sources,
            search_text=topic,
            category=request_data.get("category"),
        )
        return {
            "topic": topic,
            "mode": "keyword_fallback",
            "model": model,
            "results": [
                {
                    "article_id": article["id"],
                    "title": article.get("title"),
                    "summary": article.get("summary"),
                    "source": article.get("source"),
                    "original_link": article.get("original_link"),
                    "score": None,
                    "selection_reason": "Matched keyword fallback search because no embeddings were found.",
                }
                for article in articles
            ],
        }

    by_article: dict = {}
    for row in legacy_rows:
        score = _cosine(query_vector, row["embedding"])
        article_id = row["article_id"]
        existing = by_article.get(article_id)
        if not existing or score > existing["score"]:
            by_article[article_id] = {
                "article_id": article_id,
                "title": row.get("title"),
                "summary": row.get("summary"),
                "source": row.get("source"),
                "author": row.get("author"),
                "original_link": row.get("original_link"),
                "canonical_url": row.get("canonical_url"),
                "language": row.get("language"),
                "published_at": row.get("published_at"),
                "created_at": row.get("created_at"),
                "best_chunk_id": row.get("chunk_id"),
                "best_chunk_index": row.get("chunk_index"),
                "best_chunk_preview": (row.get("chunk_text") or "")[:500],
                "score": score,
                "selection_reason": "Selected by embedding similarity to the requested topic.",
            }

    results = sorted(by_article.values(), key=lambda item: item["score"], reverse=True)[:max_sources]
    topic_query_id = await db_manager.create_topic_query(
        topic=topic,
        language=language,
        period_days=period_days,
        max_sources=max_sources,
        metadata={"model": model, "mode": "embedding_similarity"},
    )

    return {
        "topic_query_id": topic_query_id,
        "topic": topic,
        "mode": "embedding_similarity",
        "model": model,
        "results": results,
    }


@app.post("/search/topic")
async def search_topic(request_data: dict, auth: bool = Depends(verify_api_key)):
    """Search relevant articles for an editorial topic."""
    return await build_topic_search_results(request_data)

@app.post("/reviews/critical")
async def create_critical_review(request_data: dict, auth: bool = Depends(verify_api_key)):
    """Generate and store a critical review draft for a topic."""
    global db_manager

    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    search_result = await build_topic_search_results(request_data)
    selected_articles = search_result.get("results") or []
    if not selected_articles:
        raise HTTPException(status_code=404, detail="No relevant articles found for review")

    from critical_review_generator import get_critical_review_generator

    generator = get_critical_review_generator()
    generated = await generator.generate(search_result["topic"], selected_articles)

    review_id = await db_manager.create_review(
        topic_query_id=search_result.get("topic_query_id"),
        title=generated["title"],
        review_markdown=generated["review_markdown"],
        telegram_draft=generated["telegram_draft"],
        selected_sources=[
            {
                "article_id": article["article_id"],
                "rank": index,
                "selection_reason": article.get("selection_reason"),
                "relevance_score": article.get("score"),
                "critique_summary": article.get("best_chunk_preview"),
            }
            for index, article in enumerate(selected_articles, start=1)
        ],
        metadata={
            "generator": generator.provider_name,
            "search_mode": search_result.get("mode"),
            "search_model": search_result.get("model"),
        },
    )

    return {
        "review_id": review_id,
        "topic_query_id": search_result.get("topic_query_id"),
        "topic": search_result["topic"],
        "generator": generator.provider_name,
        "selected_articles": selected_articles,
        "review_markdown": generated["review_markdown"],
        "telegram_draft": generated["telegram_draft"],
    }

@app.post("/articles")
async def create_article(article_data: dict, auth: bool = Depends(verify_api_key)):
    """Create new article with basic categorization"""
    try:
        text = article_data.get('text', '')
        title = article_data.get('title')
        source = article_data.get('source')
        telegram_user_id = article_data.get('telegram_user_id')
        
        logger.info(f"Creating article: {title}")
        
        if not text:
            return {"error": "Article text is required"}
        
        # Basic categorization
        categories = await basic_categorize(text)
        
        # Try to save to database if available
        global db_manager
        
        if db_manager:
            try:
                # Save user if telegram_user_id provided
                if telegram_user_id:
                    await db_manager.save_user(
                        telegram_user_id=telegram_user_id,
                        username=article_data.get('username'),
                        first_name=article_data.get('first_name'),
                        last_name=article_data.get('last_name')
                    )
                
                # Save article
                result = await db_manager.save_article(
                    title=title,
                    text=text,
                    summary=None,
                    source=source,
                    categories_user=categories,
                    telegram_user_id=telegram_user_id
                )
                
                if result is None:
                    # Article already exists
                    article_id = None
                    fingerprint = "duplicate"
                    status = "duplicate"
                else:
                    article_id, fingerprint = result
                    status = "created"
                
            except Exception as db_error:
                logger.warning(f"Database error, using mock data: {db_error}")
                # Fallback to mock data
                article_id = 1
                fingerprint = "mock-fingerprint"
                status = "created"
        else:
            # Database not available, use mock data
            logger.warning("Database not available, using mock data")
            article_id = 1
            fingerprint = "mock-fingerprint"
            status = "created"
        
        response_data = {
            "article_id": article_id,
            "fingerprint": fingerprint,
            "categories": categories,
            "summary": None,
            "status": status,
            "ml_service": "basic"
        }
        
        logger.info(f"Article created: {response_data}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error creating article: {e}")
        return {"error": str(e)}

@app.post("/n8n/articles")
async def create_article_n8n(article_data: dict, auth: bool = Depends(verify_api_key)):
    """Create new article from n8n with URL or text"""
    try:
        url = article_data.get('url', '')
        text = article_data.get('text', '')
        force_text = article_data.get('force_text', False)
        title = article_data.get('title', 'Untitled Article')
        source = article_data.get('source', 'n8n')
        author = article_data.get('author')
        summary = article_data.get('summary')
        language = article_data.get('language', 'en')

        logger.info(f"Creating article from n8n: {title}")

                # Check if we have either URL or text
        if not url and not text:
            raise HTTPException(
                status_code=400,
                detail="Either 'url' or 'text' is required. Provide one of them."
            )

        # If force_text is enabled, skip URL processing
        if force_text:
            url = None
            logger.info("Force text mode enabled, skipping URL processing")

        # If URL provided, extract text from it
        if url:
            try:
                logger.info(f"Starting URL extraction for: {url}")
                from text_extractor import TextExtractor
                text_extractor = TextExtractor()
                await text_extractor.initialize()

                extracted_data = await text_extractor.extract_from_url(url)
                logger.info(f"Text extraction result: {extracted_data}")

                if not extracted_data or not extracted_data.get('text'):
                    logger.error(f"Failed to extract data from URL: {url}")
                    logger.error(f"Extracted data: {extracted_data}")
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to extract text from URL. Please provide 'text' instead."
                    )

                # Use extracted data if not provided
                if not text:
                    text = extracted_data.get('text', '')
                    logger.info(f"Using extracted text, length: {len(text)}")
                if not title or title == 'Untitled Article':
                    title = extracted_data.get('title', 'Untitled Article')
                    logger.info(f"Using extracted title: {title}")
                if not summary:
                    summary = extracted_data.get('summary', '')
                    logger.info(f"Using extracted summary, length: {len(summary) if summary else 0}")

                # Close text extractor
                await text_extractor.close()
                logger.info("Text extractor closed successfully")

            except Exception as extract_error:
                logger.error(f"Error extracting text from URL: {extract_error}")
                logger.error(f"Error type: {type(extract_error).__name__}")
                logger.error(f"Error details: {str(extract_error)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to extract text from URL: {str(extract_error)}. Try one of these solutions: 1) Send text directly with 'text' field, 2) Use 'force_text': true with pre-extracted text, 3) Extract text in n8n first."
                )

        # Basic categorization - fast synchronous operation
        categories = await basic_categorize(text)

        # Try to save to database if available
        global db_manager

        if db_manager:
            try:
                # Save article
                result = await db_manager.save_article(
                    title=title,
                    text=text,
                    summary=summary,
                    source=source,
                    author=author,
                    language=language,
                    categories_user=categories,
                    telegram_user_id=None  # n8n articles don't have telegram user
                )

                if result is None:
                    # Article already exists
                    article_id = None
                    fingerprint = "duplicate"
                    status = "duplicate"
                    message = "Article already exists (duplicate content)"
                else:
                    article_id, fingerprint = result
                    status = "created"
                    message = "Article created successfully"

            except Exception as db_error:
                logger.error(f"Database error: {db_error}")
                raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        else:
            raise HTTPException(status_code=503, detail="Database not available")

        response_data = {
            "success": True,
            "article_id": article_id,
            "fingerprint": fingerprint,
            "categories": categories,
            "summary": summary,
            "status": status,
            "message": message,
            "ml_service": "basic",
            "source": "n8n",
            "processing_method": "url_extraction" if url else "direct_text",
            "url_processed": bool(url),
            "force_text_used": force_text,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Article created from n8n: {response_data}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating article from n8n: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/n8n/articles/fast")
async def create_article_n8n_fast(article_data: dict, auth: bool = Depends(verify_api_key)):
    """Fast version - only text processing, skip URL extraction"""
    try:
        text = article_data.get('text', '')
        title = article_data.get('title', 'Untitled Article')
        source = article_data.get('source', 'n8n')
        author = article_data.get('author')
        summary = article_data.get('summary')
        language = article_data.get('language', 'en')

        logger.info(f"Fast creating article from n8n: {title}")

        if not text:
            raise HTTPException(
                status_code=400,
                detail="Text is required for fast endpoint"
            )

        # Fast categorization
        categories = await basic_categorize(text)

        # Save to database
        global db_manager

        if db_manager:
            try:
                result = await db_manager.save_article(
                    title=title,
                    text=text,
                    summary=summary,
                    source=source,
                    author=author,
                    language=language,
                    categories_user=categories,
                    telegram_user_id=None
                )

                if result is None:
                    article_id = None
                    fingerprint = "duplicate"
                    status = "duplicate"
                    message = "Article already exists (duplicate content)"
                else:
                    article_id, fingerprint = result
                    status = "created"
                    message = "Article created successfully"

            except Exception as db_error:
                logger.error(f"Database error: {db_error}")
                raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        else:
            raise HTTPException(status_code=503, detail="Database not available")

        return {
            "success": True,
            "article_id": article_id,
            "fingerprint": fingerprint,
            "categories": categories,
            "status": status,
            "message": message,
            "processing_time": "fast",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in fast endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/n8n/status")
async def n8n_status(auth: bool = Depends(verify_api_key)):
    """Get API status for n8n monitoring"""
    try:
        global db_manager
        
        if db_manager:
            try:
                async with db_manager.pool.acquire() as conn:
                    articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
                    users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                    n8n_articles = await conn.fetchval(
                        "SELECT COUNT(*) FROM articles WHERE source = 'n8n'"
                    )
                
                return {
                    "status": "healthy",
                    "database": "connected",
                    "articles_total": articles_count,
                    "users_total": users_count,
                    "n8n_articles": n8n_articles,
                    "api_version": "1.0.0",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as db_error:
                logger.error(f"Database error in n8n status: {db_error}")
                return {
                    "status": "degraded",
                    "database": "error",
                    "error": str(db_error),
                    "api_version": "1.0.0",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            return {
                "status": "unavailable",
                "database": "disconnected",
                "api_version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in n8n status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "api_version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }

async def basic_categorize(text: str) -> list:
    """Basic categorization without ML service"""
    text_lower = text.lower()
    
    categories = []
    
    # Technology (английские и русские слова)
    tech_words = ['tech', 'technology', 'software', 'ai', 'machine learning', 'programming', 
                 'искусственный интеллект', 'ии', 'программирование', 'технология', 'технологии', 
                 'алгоритм', 'алгоритмы', 'машинное обучение', 'нейросеть', 'нейросети']
    if any(word in text_lower for word in tech_words):
        categories.append('Technology')
    
    # Business (английские и русские слова)
    business_words = ['business', 'finance', 'economy', 'market', 'бизнес', 'финансы', 
                     'экономика', 'рынок', 'компания', 'стартап']
    if any(word in text_lower for word in business_words):
        categories.append('Business')
    
    # Health & Science (английские и русские слова)
    health_words = ['health', 'medical', 'science', 'research', 'здоровье', 'медицина', 
                   'наука', 'исследование', 'медицинский', 'научный']
    if any(word in text_lower for word in health_words):
        categories.append('Health & Science')
    
    # Education (английские и русские слова)
    education_words = ['education', 'learning', 'study', 'course', 'образование', 'обучение', 
                      'изучение', 'курс', 'учебный', 'образовательный']
    if any(word in text_lower for word in education_words):
        categories.append('Education')
    
    if not categories:
        categories = ['General']
    
    return categories

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting Railway API server on port {port}")
    logger.info(f"Environment PORT: {os.getenv('PORT')}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
