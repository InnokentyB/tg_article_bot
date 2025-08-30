#!/usr/bin/env python3
"""
Тест подключения к базе данных Railway
"""
import asyncio
import asyncpg
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_db_connection():
    """Test database connection"""
    try:
        # Railway database URL
        database_url = "postgresql://postgres:VHpCVRLydkLVFLlJrqQGnnpEoRqBlfwD@tg-article-bot-db.railway.internal:5432/railway"
        
        logger.info("Testing Railway database connection...")
        logger.info(f"Database URL: {database_url[:30]}...")
        
        # Try to connect
        conn = await asyncpg.connect(database_url)
        
        # Test connection
        version = await conn.fetchval("SELECT version()")
        logger.info(f"✅ Connected to PostgreSQL: {version}")
        
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        existing_tables = [row['table_name'] for row in tables]
        logger.info(f"📋 Existing tables: {existing_tables}")
        
        # Test data insertion
        logger.info("🧪 Testing data insertion...")
        
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
        """, 999999999, "test_user_db", "Test", "Database")
        
        logger.info(f"✅ Test user created/updated with ID: {user_id}")
        
        # Insert test article
        article_id = await conn.fetchval("""
            INSERT INTO articles (title, text, source, telegram_user_id, categories_user)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (fingerprint) DO NOTHING
            RETURNING id
        """, "Test DB Article", "This is a test article for database connection testing.", "test_db", 999999999, ["Technology", "Test"])
        
        if article_id:
            logger.info(f"✅ Test article created with ID: {article_id}")
        else:
            logger.info("⚠️ Test article already exists (duplicate fingerprint)")
        
        # Get statistics
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
        
        logger.info(f"📊 Database statistics:")
        logger.info(f"   Users: {users_count}")
        logger.info(f"   Articles: {articles_count}")
        
        await conn.close()
        logger.info("✅ Database connection test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_db_connection())
    if not success:
        exit(1)
