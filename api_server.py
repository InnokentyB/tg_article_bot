"""
FastAPI server for article management API
"""
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from contextlib import asynccontextmanager

from database import DatabaseManager
from api_models import ArticleResponse, AdvancedCategoriesResponse, CountersUpdate, ArticleSearch, CreateArticleRequest, format_article_response

logger = logging.getLogger(__name__)

# Global components
db_manager = None
reactions_tracker = None
external_tracker = None
text_extractor = None
categorizer = None
advanced_categorizer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global db_manager, reactions_tracker, external_tracker, text_extractor, categorizer, advanced_categorizer
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Initialize tracking components
    from telegram_reactions import TelegramReactionsTracker
    from external_source_tracker import ExternalSourceTracker
    reactions_tracker = TelegramReactionsTracker(db_manager)
    external_tracker = ExternalSourceTracker(db_manager)
    await external_tracker.initialize()
    
    # Initialize article processing components
    from text_extractor import TextExtractor
    from article_categorizer import ArticleCategorizer
    from advanced_categorizer import AdvancedCategorizer
    text_extractor = TextExtractor()
    categorizer = ArticleCategorizer()
    advanced_categorizer = AdvancedCategorizer()
    
    logger.info("API server initialized")
    yield
    await db_manager.close()
    await external_tracker.close()
    logger.info("API server shutdown")

# Create FastAPI app
app = FastAPI(
    title="Article Management API",
    description="API for managing articles with categorization and search",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    """Serve demo page"""
    return FileResponse("demo.html")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "article-management-api"}

@app.get("/api/articles", response_model=List[ArticleResponse])
async def get_articles(
    limit: int = Query(50, ge=1, le=100, description="Number of articles to return"),
    offset: int = Query(0, ge=0, description="Number of articles to skip"),
    category: Optional[str] = Query(None, description="Filter by category"),
    user_id: Optional[int] = Query(None, description="Filter by Telegram user ID"),
    search_text: Optional[str] = Query(None, description="Search in title and text")
):
    """Get articles with filtering options"""
    try:
        articles = await db_manager.get_articles(
            limit=limit,
            offset=offset,
            category=category,
            user_id=user_id,
            search_text=search_text
        )
        
        # Convert to response format
        response_articles = []
        for article in articles:
            response_articles.append(format_article_response(article))
        
        return response_articles
        
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/articles/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int = Path(..., description="Article ID")
):
    """Get article by ID"""
    try:
        article = await db_manager.get_article_by_id(article_id)
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return ArticleResponse(
            id=article['id'],
            title=article['title'],
            summary=article['summary'],
            source=article['source'],
            author=article['author'],
            original_link=article['original_link'],
            categories_user=article['categories_user'] or [],
            categories_auto=article['categories_auto'] or [],
            language=article['language'],
            comments_count=article['comments_count'] or 0,
            likes_count=article['likes_count'] or 0,
            views_count=article['views_count'] or 0,
            telegram_user_id=article['telegram_user_id'],
            created_at=article['created_at'].isoformat(),
            updated_at=article['updated_at'].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article {article_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/articles/fingerprint/{fingerprint}", response_model=ArticleResponse)
async def get_article_by_fingerprint(
    fingerprint: str = Path(..., description="Article fingerprint")
):
    """Get article by fingerprint"""
    try:
        article = await db_manager.get_article_by_fingerprint(fingerprint)
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return ArticleResponse(
            id=article['id'],
            title=article['title'],
            summary=article['summary'],
            source=article['source'],
            author=article['author'],
            original_link=article['original_link'],
            categories_user=article['categories_user'] or [],
            categories_auto=article['categories_auto'] or [],
            language=article['language'],
            comments_count=article['comments_count'] or 0,
            likes_count=article['likes_count'] or 0,
            views_count=article['views_count'] or 0,
            telegram_user_id=article['telegram_user_id'],
            created_at=article['created_at'].isoformat(),
            updated_at=article['updated_at'].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article by fingerprint {fingerprint}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/articles/{article_id}/counters")
async def update_article_counters(
    counters: CountersUpdate,
    article_id: int = Path(..., description="Article ID")
):
    """Update article counters (comments, likes, views)"""
    
    try:
        # Check if article exists
        article = await db_manager.get_article_by_id(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Update counters
        await db_manager.update_counters(
            article_id=article_id,
            comments_count=counters.comments_count,
            likes_count=counters.likes_count,
            views_count=counters.views_count
        )
        
        return {"message": "Counters updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating counters for article {article_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/statistics")
async def get_statistics():
    """Get general statistics"""
    try:
        # Get basic statistics
        articles = await db_manager.get_articles(limit=10000)  # Get all articles for stats
        
        total_articles = len(articles)
        
        # Count categories
        categories = {}
        languages = {}
        sources = {}
        
        for article in articles:
            # Count auto categories
            for cat in (article.get('categories_auto') or []):
                categories[cat] = categories.get(cat, 0) + 1
            
            # Count languages
            lang = article.get('language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
            
            # Count sources
            source = article.get('source', 'unknown')
            if source and source != 'unknown':
                sources[source] = sources.get(source, 0) + 1
        
        return {
            "total_articles": total_articles,
            "categories": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)),
            "languages": dict(sorted(languages.items(), key=lambda x: x[1], reverse=True)),
            "top_sources": dict(list(sorted(sources.items(), key=lambda x: x[1], reverse=True))[:10])
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/articles/{article_id}/reactions")
async def get_article_reactions(article_id: int = Path(..., description="Article ID")):
    """Get all reactions for an article"""
    if not reactions_tracker:
        raise HTTPException(status_code=500, detail="Reactions tracker not initialized")
    
    try:
        reactions = await reactions_tracker.get_article_reactions(article_id)
        return reactions
    except Exception as e:
        logger.error(f"Error getting reactions for article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/articles/{article_id}/external-stats")
async def get_external_stats(article_id: int = Path(..., description="Article ID")):
    """Get external source statistics for an article"""
    if not external_tracker:
        raise HTTPException(status_code=500, detail="External tracker not initialized")
    
    try:
        stats = await external_tracker.get_article_external_stats(article_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting external stats for article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/articles", response_model=ArticleResponse)
async def create_article(request: CreateArticleRequest):
    """Create a new article from text or URL"""
    if not text_extractor or not categorizer or not advanced_categorizer:
        raise HTTPException(status_code=500, detail="Article processing components not initialized")
    
    if not request.text and not request.url:
        raise HTTPException(status_code=400, detail="Either text or url must be provided")
        
    try:
        # Process URL if provided
        if request.url:
            logger.info(f"Processing URL: {request.url}")
            
            # Extract content from URL
            content = await text_extractor.extract_from_url(request.url)
            if not content or not content['text']:
                raise HTTPException(status_code=400, detail="Could not extract text from URL")
            
            text = content['text']
            title = request.title or content.get('title')
            author = request.author or content.get('author')
            source = request.source or content.get('source')
            original_link = request.url
            extracted_keywords = content.get('keywords')
        else:
            # Use provided text
            logger.info("Processing provided text")
            text = request.text
            title = request.title
            author = request.author
            source = request.source
            original_link = None
            extracted_keywords = None
        
        # Check minimum text length
        if len(text) < 50:
            raise HTTPException(status_code=400, detail="Text too short (minimum 50 characters)")
        
        # Check for duplicates
        fingerprint = db_manager.generate_fingerprint(text)
        duplicate = await db_manager.check_duplicate(fingerprint)
        if duplicate:
            raise HTTPException(status_code=409, detail=f"Article already exists with ID {duplicate['id']}")
        
        # Detect language and basic categorize
        language = categorizer.detect_language(text)
        categories = categorizer.categorize_article(text, title)
        
        # Advanced categorization with AI (if available)
        advanced_categories = None
        try:
            if advanced_categorizer.is_available():
                logger.info("Running advanced categorization...")
                advanced_categories = await advanced_categorizer.categorize_article(
                    text, title, language, extracted_keywords
                )
                logger.info(f"Advanced categorization completed: {advanced_categories['primary_category']}")
        except Exception as e:
            logger.error(f"Advanced categorization failed: {e}")
        
        # Generate summary (use AI summary if available)
        summary = advanced_categories.get('summary') if advanced_categories else None
        if not summary:
            summary = text_extractor.generate_summary(text)
        
        # Save article
        article_id, _ = await db_manager.save_article(
            title=title,
            text=text,
            summary=summary,
            source=source,
            author=author,
            original_link=original_link,
            categories_advanced=advanced_categories,
            language=language,
            telegram_user_id=request.user_id
        )
        
        # Update basic categories
        await db_manager.update_article_categories(article_id, categories)
        
        # Start external tracking if source URL available
        if source and external_tracker:
            try:
                await external_tracker.track_article_source(article_id, source)
            except Exception as e:
                logger.warning(f"Failed to start external tracking: {e}")
        
        # Get saved article
        article = await db_manager.get_article_by_id(article_id)
        if not article:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved article")
        
        return format_article_response(article)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/articles/{article_id}/track-external")
async def start_external_tracking(
    article_id: int = Path(..., description="Article ID"),
    source_url: str = Query(..., description="External source URL to track")
):
    """Start tracking external source for an article"""
    if not external_tracker:
        raise HTTPException(status_code=500, detail="External tracker not initialized")
    
    try:
        await external_tracker.track_article_source(article_id, source_url)
        return {"message": f"Started tracking {source_url} for article {article_id}"}
    except Exception as e:
        logger.error(f"Error starting external tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/articles/{article_id}/telegram-link")
async def get_telegram_link(article_id: int = Path(..., description="Article ID")):
    """Get Telegram message info for an article"""
    if not reactions_tracker:
        raise HTTPException(status_code=500, detail="Reactions tracker not initialized")
    
    try:
        message_info = await reactions_tracker.get_message_info(article_id)
        if message_info:
            return message_info
        else:
            raise HTTPException(status_code=404, detail="No Telegram message linked to this article")
    except Exception as e:
        logger.error(f"Error getting telegram link for article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/external/update-all")
async def update_all_external_stats():
    """Update external statistics for all tracked articles"""
    if not external_tracker:
        raise HTTPException(status_code=500, detail="External tracker not initialized")
    
    try:
        await external_tracker.update_all_tracked_articles()
        return {"message": "Started updating external statistics for all tracked articles"}
    except Exception as e:
        logger.error(f"Error updating all external stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)