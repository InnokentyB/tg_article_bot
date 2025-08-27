# Telegram Article Management Bot

## Overview

This is a Telegram bot system for article management that allows users to save articles by sending text or URLs, automatically categorizes them, and provides a REST API for article management. The system includes duplicate detection, language identification, and simple keyword-based categorization.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (August 8, 2025)

✓ Complete rewrite from RSS system to Telegram bot system
✓ Created PostgreSQL database schema for articles and users  
✓ Built Telegram bot with aiogram for article processing
✓ Added REST API with FastAPI for article management
✓ Implemented text extraction from URLs using readability-lxml
✓ Added simple keyword-based categorization system
✓ Created duplicate detection using SHA256 fingerprints
✓ Implemented FSM-based callback handling for user categories
✓ Added multi-project bot token management system
✓ Fixed webhook conflicts with automatic deletion on startup
✓ Created config.py for centralized configuration management

**Latest Updates:**
✓ Added Telegram message linking and reaction tracking system
✓ Implemented external source statistics tracking (Habr, Medium, DEV.to)
✓ Created TelegramReactionsTracker for monitoring message engagement
✓ Built ExternalSourceTracker for web scraping article statistics
✓ Extended database schema with reactions and external stats tables
✓ Added comprehensive API endpoints for reactions and external statistics
✓ Configured Bot API 7.0+ reaction update handling
✓ Enabled real-time tracking of article engagement across platforms

**August 17, 2025 - Advanced AI Categorization Integration:**
✓ Integrated advanced AI categorization service using OpenAI GPT-4 mini
✓ Extended database schema with categories_advanced JSON field
✓ Implemented dual categorization system (basic + AI-powered)
✓ Added AdvancedCategorizer module with embeddings and text analysis
✓ Enhanced Telegram bot to use AI categorization when OpenAI key available
✓ Updated API models to include structured advanced categorization data
✓ Created comprehensive test suite for advanced categorizer validation
✓ Added graceful degradation when OpenAI API key is unavailable
✓ Fixed JSON serialization for categories_advanced database storage
✓ System fully operational with proper error handling and data integrity
✓ Improved text extraction quality with trafilatura integration and enhanced cleaning
✓ Enhanced categorization logic with top-3 analysis and confidence boosting
✓ Expanded category system from 10 to 12 categories (added Management, Career)
✓ Increased text extraction volume from ~500 to 8907+ characters per article

## System Architecture

The application follows a modular architecture with clear separation of concerns:

### Core Components
- **Telegram Bot**: aiogram-based bot for receiving articles (text/URLs)
- **Text Extractor**: Extracts content from URLs using readability-lxml and BeautifulSoup
- **Article Categorizer**: Simple keyword-based categorization system
- **Advanced Categorizer**: AI-powered categorization using OpenAI GPT-4 mini with embeddings
- **Database Manager**: PostgreSQL interaction using asyncpg
- **REST API**: FastAPI server for article management and statistics
- **Telegram Reactions Tracker**: Monitors message reactions and engagement metrics
- **External Source Tracker**: Web scraper for article statistics from Habr, Medium, DEV.to

### Technology Stack
- **Backend**: Python with FastAPI for REST API and aiogram for Telegram bot
- **Database**: PostgreSQL with asyncpg for async operations
- **Text Processing**: readability-lxml, BeautifulSoup4, langdetect
- **Machine Learning**: scikit-learn for TF-IDF keyword extraction, OpenAI GPT-4 mini for advanced categorization
- **AI Services**: OpenAI API for embeddings and text analysis
- **External APIs**: Telegram Bot API for message handling

## Key Components

### Database Schema (PostgreSQL)
```sql
articles (
    id SERIAL PRIMARY KEY,
    title TEXT,
    text TEXT NOT NULL,
    summary TEXT,
    fingerprint VARCHAR(64) UNIQUE NOT NULL,
    source TEXT,
    author TEXT,
    is_translated BOOLEAN DEFAULT FALSE,
    original_link TEXT,
    categories_user TEXT[],
    categories_auto TEXT[],
    categories_advanced JSONB,
    primary_category VARCHAR(100),
    subcategories TEXT[],
    keywords TEXT[],
    confidence FLOAT,
    language VARCHAR(10),
    comments_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    telegram_user_id BIGINT,
    telegram_message_id BIGINT,
    telegram_chat_id BIGINT,
    external_stats JSONB,
    last_stats_update TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

users (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

article_reactions (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    telegram_user_id BIGINT,
    reaction_emoji VARCHAR(10),
    reaction_type VARCHAR(20) DEFAULT 'telegram',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(article_id, telegram_user_id, reaction_type)
)

external_source_stats (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    source_type VARCHAR(20),
    source_url TEXT,
    views_count INTEGER DEFAULT 0,
    external_comments_count INTEGER DEFAULT 0,
    external_likes_count INTEGER DEFAULT 0,
    external_bookmarks_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(article_id, source_type)
)
```

### Configuration Management

**Multi-Project Bot Token Management:**
- `ARTICLE_BOT_TOKEN` - Токен для бота управления статьями (этот проект)
- `ARTICLE_BOT_WEBHOOK_URL` - URL вебхука для бота статей (опционально)
- Система legacy поддержки автоматически использует `TELEGRAM_BOT_TOKEN` если новые переменные не установлены
- Отдельные токены для разных проектов предотвращают конфликты

**Основная конфигурация:**
- PostgreSQL database connection via `DATABASE_URL`
- Optional OpenAI integration for advanced categorization
- FSM-based callback handling with memory storage
- Automatic webhook management for polling mode

### Content Processing Pipeline
1. **Fetch**: RSS parsing with feedparser
2. **Extract**: Full text extraction using trafilatura
3. **Filter Stage 1**: Tag-based filtering against allowed categories
4. **Filter Stage 2**: AI-powered content relevance analysis
5. **Categorize**: AI classification into predefined categories
6. **Generate**: Editorial review creation (300-500 characters)
7. **Store**: Database persistence with metadata
8. **Publish**: Automated Telegram posting (optional)

## Data Flow

```
RSS Feed → Parse → Extract Text → Tag Filter → AI Filter → Categorize → Generate Review → Store → Publish
```

The system maintains article state throughout the pipeline, preventing duplicate processing and enabling manual review before publication.

## External Dependencies

### Required Services
- **OpenAI API**: For content analysis and review generation (GPT-4o model)
- **Telegram Bot API**: For automated publishing to channels/groups

### Python Libraries
- `feedparser`: RSS feed parsing
- `trafilatura`: Web content extraction
- `openai`: AI integration
- `flask`: Web interface
- `requests`: HTTP operations
- `sqlite3`: Database operations
- `schedule`: Automated task scheduling

### Content Processing
- Tag-based filtering using configurable allowed tags
- AI-powered relevance scoring and categorization
- Similarity detection to prevent duplicate content
- Minimum content length filtering

## Deployment Strategy

### Local Development
- SQLite database for quick setup
- Environment variables via `.env` file
- Flask development server
- Background scheduler in separate thread

### Production Considerations
- Database can be upgraded to PostgreSQL with minimal changes
- Scheduler can be replaced with cron jobs or cloud functions
- Web interface can be deployed as separate service
- Rate limiting and error handling for external APIs

### Configuration
The system is designed for easy deployment with:
- Single entry point (`main.py`)
- Environment-based configuration
- Modular architecture allowing component replacement
- Comprehensive logging for monitoring and debugging

### Scalability
- Database abstraction layer supports easy migration to PostgreSQL
- Modular design allows horizontal scaling of individual components
- Stateless processing pipeline enables parallel execution
- Background job system can be replaced with queue-based solutions