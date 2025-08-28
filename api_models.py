"""
Pydantic models for API responses
"""
from pydantic import BaseModel
from typing import List, Optional, Dict

class AdvancedCategoriesResponse(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    primary_category: Optional[str] = None
    primary_category_label: Optional[str] = None
    subcategories: List[str] = []
    keywords: List[str] = []
    confidence: Optional[float] = None
    # New triple categorization fields
    ai_categorization: Optional[Dict] = None
    topic_clustering: Optional[Dict] = None
    bart_categorization: Optional[Dict] = None

class ArticleResponse(BaseModel):
    id: int
    title: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    original_link: Optional[str] = None
    categories_user: List[str] = []
    categories_auto: List[str] = []
    categories_advanced: Optional[AdvancedCategoriesResponse] = None
    language: Optional[str] = None
    comments_count: int = 0
    likes_count: int = 0
    views_count: int = 0
    telegram_user_id: Optional[int] = None
    created_at: str
    updated_at: str

class CountersUpdate(BaseModel):
    comments_count: Optional[int] = None
    likes_count: Optional[int] = None
    views_count: Optional[int] = None

class ArticleSearch(BaseModel):
    limit: int = 50
    offset: int = 0
    category: Optional[str] = None
    user_id: Optional[int] = None
    search_text: Optional[str] = None

class CreateArticleRequest(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    user_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Содержимое статьи...",
                "url": "https://example.com/article", 
                "title": "Заголовок статьи",
                "author": "Автор",
                "source": "Источник",
                "user_id": 12345
            }
        }

def format_article_response(article: dict) -> ArticleResponse:
    """Helper function to format article dict to ArticleResponse"""
    import json
    
    # Handle advanced categories - parse JSON string if needed
    advanced_cat = None
    if article.get('categories_advanced'):
        categories_data = article['categories_advanced']
        if isinstance(categories_data, str):
            try:
                categories_data = json.loads(categories_data)
            except (json.JSONDecodeError, TypeError):
                categories_data = None
        
        if categories_data and isinstance(categories_data, dict):
            # Handle new triple categorization format
            if 'ai_categorization' in categories_data or 'topic_clustering' in categories_data or 'bart_categorization' in categories_data:
                # New format with triple categorization
                advanced_cat = AdvancedCategoriesResponse(
                    id=categories_data.get('id'),
                    title=categories_data.get('title'),
                    summary=categories_data.get('summary'),
                    primary_category=categories_data.get('primary_category'),
                    primary_category_label=categories_data.get('primary_category_label'),
                    subcategories=categories_data.get('subcategories', []),
                    keywords=categories_data.get('keywords', []),
                    confidence=categories_data.get('confidence'),
                    ai_categorization=categories_data.get('ai_categorization'),
                    topic_clustering=categories_data.get('topic_clustering'),
                    bart_categorization=categories_data.get('bart_categorization')
                )
            else:
                # Legacy format - backward compatibility
                advanced_cat = AdvancedCategoriesResponse(**categories_data)
    
    return ArticleResponse(
        id=article['id'],
        title=article['title'],
        summary=article['summary'],
        source=article['source'],
        author=article['author'],
        original_link=article['original_link'],
        categories_user=article['categories_user'] or [],
        categories_auto=article['categories_auto'] or [],
        categories_advanced=advanced_cat,
        language=article['language'],
        comments_count=article['comments_count'] or 0,
        likes_count=article['likes_count'] or 0,
        views_count=article['views_count'] or 0,
        telegram_user_id=article['telegram_user_id'],
        created_at=article['created_at'].isoformat(),
        updated_at=article['updated_at'].isoformat()
    )