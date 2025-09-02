"""
External source statistics tracker for Habr, Medium, etc.
"""
import logging
import re
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import aiohttp
from trafilatura import fetch_url
from bs4 import BeautifulSoup
from database import DatabaseManager

logger = logging.getLogger(__name__)

class ExternalSourceTracker:
    """Tracks statistics from external sources like Habr, Medium, etc."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.session = None
        
        # Source-specific parsers
        self.source_parsers = {
            'habr.com': self.parse_habr_stats,
            'medium.com': self.parse_medium_stats,
            'dev.to': self.parse_dev_stats
        }
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def track_article_source(self, article_id: int, source_url: str):
        """Start tracking external source for an article"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
        
        # Determine source type
        source_type = self.detect_source_type(source_url)
        if not source_type:
            logger.warning(f"Unsupported source URL: {source_url}")
            return
        
        # Save initial tracking record
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO external_source_stats 
                   (article_id, source_type, source_url, last_updated)
                   VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                   ON CONFLICT (article_id, source_type)
                   DO UPDATE SET source_url = $3, last_updated = CURRENT_TIMESTAMP""",
                article_id, source_type, source_url
            )
        
        # Fetch initial stats
        await self.update_source_stats(article_id, source_type, source_url)
        logger.info(f"Started tracking {source_type} for article {article_id}")
    
    def detect_source_type(self, url: str) -> Optional[str]:
        """Detect source type from URL"""
        for domain, _ in self.source_parsers.items():
            if domain in url.lower():
                return domain.split('.')[0]  # 'habr', 'medium', etc.
        return None
    
    async def update_source_stats(self, article_id: int, source_type: str, source_url: str):
        """Update statistics for external source"""
        try:
            parser_key = f"{source_type}.com"
            if parser_key not in self.source_parsers:
                logger.warning(f"No parser for source type: {source_type}")
                return
            
            # Fetch and parse page
            stats = await self.source_parsers[parser_key](source_url)
            if not stats:
                logger.warning(f"Failed to parse stats from {source_url}")
                return
            
            # Save to database
            await self.save_external_stats(article_id, source_type, stats)
            logger.info(f"Updated {source_type} stats for article {article_id}: {stats}")
            
        except Exception as e:
            logger.error(f"Error updating stats for {source_url}: {e}")
    
    async def parse_habr_stats(self, url: str) -> Optional[Dict]:
        """Parse Habr article statistics"""
        try:
            # Use trafilatura to fetch content
            downloaded = fetch_url(url)
            if not downloaded:
                return None
                
            soup = BeautifulSoup(downloaded, 'html.parser')
            
            stats = {
                'views_count': 0,
                'comments_count': 0,
                'likes_count': 0,
                'bookmarks_count': 0
            }
            
            # Parse views (обычно в классе tm-icon-counter__value)
            views_elem = soup.find('span', class_='tm-icon-counter__value')
            if views_elem:
                views_text = views_elem.get_text(strip=True)
                stats['views_count'] = self.parse_count_value(views_text)
            
            # Parse comments (ищем элементы с комментариями)
            comments_elem = soup.find('a', href=re.compile(r'#comments'))
            if comments_elem:
                comments_text = comments_elem.get_text(strip=True)
                stats['comments_count'] = self.parse_count_value(comments_text)
            
            # Parse rating/likes (класс tm-votes-meter__value)
            rating_elem = soup.find('span', class_='tm-votes-meter__value')
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_value = self.parse_count_value(rating_text, allow_negative=True)
                stats['likes_count'] = max(0, rating_value)  # Only positive ratings
            
            # Parse bookmarks (класс bookmarks-button__counter)
            bookmarks_elem = soup.find('span', class_='bookmarks-button__counter')
            if bookmarks_elem:
                bookmarks_text = bookmarks_elem.get_text(strip=True)
                stats['bookmarks_count'] = self.parse_count_value(bookmarks_text)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error parsing Habr stats: {e}")
            return None
    
    async def parse_medium_stats(self, url: str) -> Optional[Dict]:
        """Parse Medium article statistics"""
        try:
            if not self.session:
                await self.initialize()
                
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                stats = {
                    'views_count': 0,
                    'comments_count': 0,
                    'likes_count': 0,
                    'bookmarks_count': 0
                }
                
                # Medium claps (likes)
                claps_elem = soup.find('button', {'aria-label': re.compile(r'clap', re.I)})
                if claps_elem:
                    claps_text = claps_elem.get_text(strip=True)
                    stats['likes_count'] = self.parse_count_value(claps_text)
                
                # Medium responses (comments)
                responses_elem = soup.find('a', href=re.compile(r'responses'))
                if responses_elem:
                    responses_text = responses_elem.get_text(strip=True)
                    stats['comments_count'] = self.parse_count_value(responses_text)
                
                return stats
                
        except Exception as e:
            logger.error(f"Error parsing Medium stats: {e}")
            return None
    
    async def parse_dev_stats(self, url: str) -> Optional[Dict]:
        """Parse DEV.to article statistics"""
        try:
            if not self.session:
                await self.initialize()
                
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                stats = {
                    'views_count': 0,
                    'comments_count': 0,
                    'likes_count': 0,
                    'bookmarks_count': 0
                }
                
                # DEV reactions
                reactions_elem = soup.find('span', class_='aggregate_reactions_counter')
                if reactions_elem:
                    reactions_text = reactions_elem.get_text(strip=True)
                    stats['likes_count'] = self.parse_count_value(reactions_text)
                
                # DEV comments
                comments_elem = soup.find('a', href=re.compile(r'#comments'))
                if comments_elem:
                    comments_text = comments_elem.get_text(strip=True)
                    stats['comments_count'] = self.parse_count_value(comments_text)
                
                return stats
                
        except Exception as e:
            logger.error(f"Error parsing DEV.to stats: {e}")
            return None
    
    def parse_count_value(self, text: str, allow_negative: bool = False) -> int:
        """Parse numeric count from text (handles K, M suffixes)"""
        if not text:
            return 0
            
        # Clean text
        text = re.sub(r'[^\d\.,kmKM+-]', '', text)
        if not text or text in ['+', '-']:
            return 0
        
        # Handle negative numbers
        negative = text.startswith('-')
        text = text.lstrip('+-')
        
        try:
            # Handle K/M suffixes
            multiplier = 1
            if text.lower().endswith('k'):
                multiplier = 1000
                text = text[:-1]
            elif text.lower().endswith('m'):
                multiplier = 1000000
                text = text[:-1]
            
            # Parse number
            number = float(text.replace(',', ''))
            result = int(number * multiplier)
            
            if negative and allow_negative:
                result = -result
            elif negative and not allow_negative:
                result = 0
                
            return max(0, result) if not allow_negative else result
            
        except ValueError:
            return 0
    
    async def save_external_stats(self, article_id: int, source_type: str, stats: Dict):
        """Save external statistics to database"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """UPDATE external_source_stats 
                   SET views_count = $3, external_comments_count = $4, 
                       external_likes_count = $5, external_bookmarks_count = $6,
                       last_updated = CURRENT_TIMESTAMP
                   WHERE article_id = $1 AND source_type = $2""",
                article_id, source_type,
                stats.get('views_count', 0),
                stats.get('comments_count', 0), 
                stats.get('likes_count', 0),
                stats.get('bookmarks_count', 0)
            )
            
            # Also update main article stats
            await conn.execute(
                """UPDATE articles 
                   SET external_stats = COALESCE(external_stats, '{}'::jsonb) || $2::jsonb,
                       last_stats_update = CURRENT_TIMESTAMP
                   WHERE id = $1""",
                article_id, 
                json.dumps({f'{source_type}_stats': stats})
            )
    
    async def get_article_external_stats(self, article_id: int) -> Dict:
        """Get all external statistics for an article"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.db.pool.acquire() as conn:
            external_stats = await conn.fetch(
                """SELECT source_type, source_url, views_count, external_comments_count,
                          external_likes_count, external_bookmarks_count, last_updated
                   FROM external_source_stats 
                   WHERE article_id = $1""",
                article_id
            )
            
            result = {}
            for stat in external_stats:
                result[stat['source_type']] = {
                    'url': stat['source_url'],
                    'views': stat['views_count'],
                    'comments': stat['external_comments_count'],
                    'likes': stat['external_likes_count'],
                    'bookmarks': stat['external_bookmarks_count'],
                    'last_updated': stat['last_updated']
                }
            
            return result
    
    async def update_all_tracked_articles(self):
        """Update stats for all tracked articles (can be run periodically)"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
        
        # Get articles that need updating (older than 1 hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        async with self.db.pool.acquire() as conn:
            articles_to_update = await conn.fetch(
                """SELECT article_id, source_type, source_url 
                   FROM external_source_stats 
                   WHERE last_updated < $1""",
                cutoff_time
            )
        
        logger.info(f"Updating stats for {len(articles_to_update)} articles")
        
        for article_info in articles_to_update:
            try:
                await self.update_source_stats(
                    article_info['article_id'],
                    article_info['source_type'], 
                    article_info['source_url']
                )
            except Exception as e:
                logger.error(f"Failed to update stats for article {article_info['article_id']}: {e}")