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

async def init_database():
    """Initialize database with schema"""
    try:
        # Get database URL from Railway
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL not found in environment variables")
            return False
        
        logger.info("Connecting to Railway database...")
        
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        # Read and execute init.sql
        with open('init.sql', 'r', encoding='utf-8') as f:
            init_sql = f.read()
        
        logger.info("Executing database schema...")
        await conn.execute(init_sql)
        
        logger.info("Database schema initialized successfully!")
        
        # Test connection
        result = await conn.fetchval("SELECT COUNT(*) FROM users")
        logger.info(f"Database test: {result} users found")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(init_database())
    if success:
        logger.info("Database initialization completed successfully!")
    else:
        logger.error("Database initialization failed!")
        exit(1)
