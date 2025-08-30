#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных в Railway
"""
import asyncio
import asyncpg
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_railway_database():
    """Initialize Railway database"""
    try:
        # Get database URL from Railway
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL not found in environment variables")
            logger.info("Available environment variables:")
            for key, value in os.environ.items():
                if 'DATABASE' in key or 'POSTGRES' in key or 'DB' in key:
                    logger.info(f"  {key}: {value}")
            return False
        
        logger.info("Connecting to Railway database...")
        logger.info(f"Database URL: {database_url[:20]}...")  # Show only beginning for security
        
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        # Test connection
        version = await conn.fetchval("SELECT version()")
        logger.info(f"Connected to PostgreSQL: {version}")
        
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        existing_tables = [row['table_name'] for row in tables]
        logger.info(f"Existing tables: {existing_tables}")
        
        # Create tables if they don't exist
        if 'users' not in existing_tables:
            logger.info("Creating users table...")
            await conn.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    telegram_user_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            logger.info("Users table created successfully!")
        
        if 'articles' not in existing_tables:
            logger.info("Creating articles table...")
            await conn.execute("""
                CREATE TABLE articles (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    text TEXT NOT NULL,
                    summary TEXT,
                    fingerprint VARCHAR(64) UNIQUE,
                    source VARCHAR(500),
                    author VARCHAR(200),
                    original_link TEXT,
                    is_translated BOOLEAN DEFAULT FALSE,
                    categories_user TEXT[],
                    categories_auto TEXT[],
                    categories_advanced JSONB,
                    language VARCHAR(10),
                    comments_count INTEGER DEFAULT 0,
                    likes_count INTEGER DEFAULT 0,
                    views_count INTEGER DEFAULT 0,
                    telegram_user_id BIGINT REFERENCES users(telegram_user_id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            logger.info("Articles table created successfully!")
        
        if 'article_reactions' not in existing_tables:
            logger.info("Creating article_reactions table...")
            await conn.execute("""
                CREATE TABLE article_reactions (
                    id SERIAL PRIMARY KEY,
                    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                    telegram_user_id BIGINT REFERENCES users(telegram_user_id) ON DELETE CASCADE,
                    reaction_type VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(article_id, telegram_user_id, reaction_type)
                )
            """)
            logger.info("Article reactions table created successfully!")
        
        if 'external_tracking' not in existing_tables:
            logger.info("Creating external_tracking table...")
            await conn.execute("""
                CREATE TABLE external_tracking (
                    id SERIAL PRIMARY KEY,
                    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                    external_url TEXT NOT NULL,
                    external_title TEXT,
                    external_summary TEXT,
                    tracking_type VARCHAR(50) NOT NULL,
                    external_id VARCHAR(100),
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            logger.info("External tracking table created successfully!")
        
        if 'schema_migrations' not in existing_tables:
            logger.info("Creating schema_migrations table...")
            await conn.execute("""
                CREATE TABLE schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    checksum VARCHAR(64) NOT NULL
                )
            """)
            logger.info("Schema migrations table created successfully!")
        
        # Create indexes
        logger.info("Creating indexes...")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_fingerprint ON articles(fingerprint)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_telegram_user_id ON articles(telegram_user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles USING GIN(categories_user)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_article_reactions_article_id ON article_reactions(article_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_article_reactions_user_id ON article_reactions(telegram_user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_external_tracking_article_id ON external_tracking(article_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_external_tracking_type ON external_tracking(tracking_type)")
        logger.info("Indexes created successfully!")
        
        # Test data insertion
        logger.info("Testing data insertion...")
        
        # Insert test user
        user_id = await conn.fetchval("""
            INSERT INTO users (telegram_user_id, username, first_name, last_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (telegram_user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                updated_at = NOW()
            RETURNING id
        """, 123456789, "test_user", "Test", "User")
        
        logger.info(f"Test user created/updated with ID: {user_id}")
        
        # Insert test article
        article_id = await conn.fetchval("""
            INSERT INTO articles (title, text, source, telegram_user_id, categories_user)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (fingerprint) DO NOTHING
            RETURNING id
        """, "Test Article", "This is a test article for database initialization.", "test", 123456789, ["Technology", "Test"])
        
        if article_id:
            logger.info(f"Test article created with ID: {article_id}")
        else:
            logger.info("Test article already exists (duplicate fingerprint)")
        
        # Get final statistics
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
        
        logger.info(f"Database initialization completed!")
        logger.info(f"Users in database: {users_count}")
        logger.info(f"Articles in database: {articles_count}")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(init_railway_database())
    if success:
        logger.info("Database initialization completed successfully!")
    else:
        logger.error("Database initialization failed!")
        exit(1)
