#!/usr/bin/env python3
"""
Система миграций для базы данных
"""
import asyncio
import asyncpg
import os
import logging
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationManager:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        self.migrations_table = 'schema_migrations'
        
    async def create_migrations_table(self, conn):
        """Create migrations tracking table"""
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                id SERIAL PRIMARY KEY,
                version VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                checksum VARCHAR(64) NOT NULL
            )
        """)
    
    async def get_applied_migrations(self, conn) -> List[str]:
        """Get list of applied migration versions"""
        rows = await conn.fetch(f"SELECT version FROM {self.migrations_table} ORDER BY id")
        return [row['version'] for row in rows]
    
    async def apply_migration(self, conn, version: str, name: str, sql: str):
        """Apply a single migration"""
        # Calculate checksum
        import hashlib
        checksum = hashlib.sha256(sql.encode('utf-8')).hexdigest()
        
        # Apply migration
        await conn.execute(sql)
        
        # Record migration
        await conn.execute(f"""
            INSERT INTO {self.migrations_table} (version, name, checksum)
            VALUES ($1, $2, $3)
        """, version, name, checksum)
        
        logger.info(f"Applied migration: {version} - {name}")
    
    def get_migrations(self) -> List[Dict]:
        """Get list of available migrations"""
        return [
            {
                'version': '001',
                'name': 'Initial schema',
                'sql': '''
                -- Create users table
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_user_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );

                -- Create articles table
                CREATE TABLE IF NOT EXISTS articles (
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
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_articles_fingerprint ON articles(fingerprint);
                CREATE INDEX IF NOT EXISTS idx_articles_telegram_user_id ON articles(telegram_user_id);
                CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at);
                CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles USING GIN(categories_user);
                '''
            },
            {
                'version': '002',
                'name': 'Add article reactions table',
                'sql': '''
                -- Create article reactions table
                CREATE TABLE IF NOT EXISTS article_reactions (
                    id SERIAL PRIMARY KEY,
                    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                    telegram_user_id BIGINT REFERENCES users(telegram_user_id) ON DELETE CASCADE,
                    reaction_type VARCHAR(20) NOT NULL, -- like, dislike, bookmark
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(article_id, telegram_user_id, reaction_type)
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_article_reactions_article_id ON article_reactions(article_id);
                CREATE INDEX IF NOT EXISTS idx_article_reactions_user_id ON article_reactions(telegram_user_id);
                '''
            },
            {
                'version': '003',
                'name': 'Add external tracking table',
                'sql': '''
                -- Create external tracking table
                CREATE TABLE IF NOT EXISTS external_tracking (
                    id SERIAL PRIMARY KEY,
                    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                    external_url TEXT NOT NULL,
                    external_title TEXT,
                    external_summary TEXT,
                    tracking_type VARCHAR(50) NOT NULL, -- telegram, twitter, reddit, etc.
                    external_id VARCHAR(100),
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_external_tracking_article_id ON external_tracking(article_id);
                CREATE INDEX IF NOT EXISTS idx_external_tracking_type ON external_tracking(tracking_type);
                '''
            }
        ]
    
    async def run_migrations(self):
        """Run all pending migrations"""
        try:
            logger.info("Starting database migrations...")
            
            conn = await asyncpg.connect(self.db_url)
            
            # Create migrations table
            await self.create_migrations_table(conn)
            
            # Get applied migrations
            applied_versions = await self.get_applied_migrations(conn)
            logger.info(f"Applied migrations: {applied_versions}")
            
            # Get available migrations
            available_migrations = self.get_migrations()
            
            # Apply pending migrations
            for migration in available_migrations:
                if migration['version'] not in applied_versions:
                    logger.info(f"Applying migration {migration['version']}: {migration['name']}")
                    await self.apply_migration(conn, migration['version'], migration['name'], migration['sql'])
                else:
                    logger.info(f"Migration {migration['version']} already applied")
            
            await conn.close()
            logger.info("Database migrations completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

async def main():
    """Main migration function"""
    manager = MigrationManager()
    success = await manager.run_migrations()
    if not success:
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
