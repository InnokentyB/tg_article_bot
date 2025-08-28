"""
Database management for RSS Article Processing System
"""
import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager
import json
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv('DATABASE_PATH', 'articles.db')
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create articles table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        url TEXT UNIQUE NOT NULL,
                        text TEXT NOT NULL,
                        tags TEXT,  -- JSON array
                        category TEXT,
                        cluster_id INTEGER,
                        summary TEXT,
                        posted BOOLEAN DEFAULT FALSE,
                        published DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        source TEXT DEFAULT 'rss'
                    )
                ''')
                
                # Create processing logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processing_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        articles_processed INTEGER DEFAULT 0,
                        articles_published INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'success',
                        error_message TEXT,
                        processing_time_seconds REAL
                    )
                ''')
                
                # Create configuration table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS configuration (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_posted ON articles(posted)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def save_article(self, article):
        """Save article to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Prepare data
                tags_json = json.dumps(article.get('tags', []))
                published = article.get('published')
                if isinstance(published, datetime):
                    published = published.isoformat()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO articles 
                    (title, url, text, tags, category, summary, published, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article.get('title', ''),
                    article.get('url', ''),
                    article.get('text', ''),
                    tags_json,
                    article.get('category', ''),
                    article.get('summary', ''),
                    published,
                    article.get('source', 'rss')
                ))
                
                article_id = cursor.lastrowid
                conn.commit()
                
                logger.debug(f"Saved article with ID: {article_id}")
                return article_id
                
        except Exception as e:
            logger.error(f"Error saving article: {str(e)}")
            raise
    
    def article_exists(self, url):
        """Check if article already exists in database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM articles WHERE url = ?', (url,))
                result = cursor.fetchone()
                return result is not None
                
        except Exception as e:
            logger.error(f"Error checking article existence: {str(e)}")
            return False
    
    def mark_as_posted(self, article_id):
        """Mark article as posted to Telegram"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE articles 
                    SET posted = TRUE, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (article_id,))
                conn.commit()
                
                logger.debug(f"Marked article {article_id} as posted")
                
        except Exception as e:
            logger.error(f"Error marking article as posted: {str(e)}")
            raise
    
    def get_articles(self, limit=50, category=None, posted=None):
        """Get articles from database with optional filtering"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM articles WHERE 1=1'
                params = []
                
                if category:
                    query += ' AND category = ?'
                    params.append(category)
                
                if posted is not None:
                    query += ' AND posted = ?'
                    params.append(posted)
                
                query += ' ORDER BY created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                articles = []
                for row in rows:
                    article = dict(row)
                    # Parse JSON tags
                    try:
                        article['tags'] = json.loads(article['tags']) if article['tags'] else []
                    except:
                        article['tags'] = []
                    articles.append(article)
                
                return articles
                
        except Exception as e:
            logger.error(f"Error getting articles: {str(e)}")
            return []
    
    def get_article_by_id(self, article_id):
        """Get specific article by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
                row = cursor.fetchone()
                
                if row:
                    article = dict(row)
                    try:
                        article['tags'] = json.loads(article['tags']) if article['tags'] else []
                    except:
                        article['tags'] = []
                    return article
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting article by ID: {str(e)}")
            return None
    
    def get_statistics(self):
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total articles
                cursor.execute('SELECT COUNT(*) as total FROM articles')
                total = cursor.fetchone()['total']
                
                # Posted articles
                cursor.execute('SELECT COUNT(*) as posted FROM articles WHERE posted = TRUE')
                posted = cursor.fetchone()['posted']
                
                # Articles by category
                cursor.execute('''
                    SELECT category, COUNT(*) as count 
                    FROM articles 
                    WHERE category IS NOT NULL AND category != ''
                    GROUP BY category 
                    ORDER BY count DESC
                ''')
                categories = [dict(row) for row in cursor.fetchall()]
                
                # Recent processing logs
                cursor.execute('''
                    SELECT * FROM processing_logs 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                ''')
                recent_logs = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'total_articles': total,
                    'posted_articles': posted,
                    'unpublished_articles': total - posted,
                    'categories': categories,
                    'recent_logs': recent_logs
                }
                
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}
    
    def log_processing(self, articles_processed, articles_published, processing_time, status='success', error_message=None):
        """Log processing run"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO processing_logs 
                    (articles_processed, articles_published, processing_time_seconds, status, error_message)
                    VALUES (?, ?, ?, ?, ?)
                ''', (articles_processed, articles_published, processing_time, status, error_message))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error logging processing: {str(e)}")
    
    def get_unpublished_articles(self, limit=10):
        """Get articles that haven't been published yet"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM articles 
                    WHERE posted = FALSE 
                    ORDER BY created_at ASC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                articles = []
                for row in rows:
                    article = dict(row)
                    try:
                        article['tags'] = json.loads(article['tags']) if article['tags'] else []
                    except:
                        article['tags'] = []
                    articles.append(article)
                
                return articles
                
        except Exception as e:
            logger.error(f"Error getting unpublished articles: {str(e)}")
            return []
    
    def cleanup_old_articles(self, days=30):
        """Remove articles older than specified days"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM articles 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old articles")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old articles: {str(e)}")
            return 0
