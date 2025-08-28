"""
RSS parsing and article content extraction
"""
import feedparser
import requests
import trafilatura
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
import time

logger = logging.getLogger(__name__)

class RSSParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch_articles(self, rss_url):
        """Fetch and parse articles from RSS feed"""
        try:
            logger.info(f"Fetching RSS feed: {rss_url}")
            
            # Parse RSS feed
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                logger.warning(f"RSS feed has issues: {feed.bozo_exception}")
            
            articles = []
            
            for entry in feed.entries:
                try:
                    article = self._parse_entry(entry)
                    if article:
                        articles.append(article)
                        
                    # Rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error parsing entry: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {rss_url}: {str(e)}")
            return []
    
    def _parse_entry(self, entry):
        """Parse individual RSS entry"""
        try:
            # Extract basic information
            title = entry.get('title', '').strip()
            url = entry.get('link', '').strip()
            
            if not title or not url:
                logger.debug("Skipping entry: missing title or URL")
                return None
            
            # Extract tags/categories
            tags = []
            if hasattr(entry, 'tags'):
                tags.extend([tag.term.lower() for tag in entry.tags if hasattr(tag, 'term')])
            
            if hasattr(entry, 'category'):
                if isinstance(entry.category, str):
                    tags.append(entry.category.lower())
                elif isinstance(entry.category, list):
                    tags.extend([cat.lower() for cat in entry.category if isinstance(cat, str)])
            
            # Extract publication date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])
            else:
                published = datetime.now()
            
            # Extract full article text
            text = self._extract_article_text(url)
            
            if not text or len(text) < 200:
                logger.debug(f"Skipping article: insufficient text content - {title}")
                return None
            
            # Extract summary if available
            summary = entry.get('summary', '').strip()
            
            article = {
                'title': title,
                'url': url,
                'text': text,
                'summary': summary,
                'tags': tags,
                'published': published,
                'source': 'rss'
            }
            
            logger.debug(f"Parsed article: {title}")
            return article
            
        except Exception as e:
            logger.error(f"Error parsing entry: {str(e)}")
            return None
    
    def _extract_article_text(self, url):
        """Extract full text content from article URL"""
        try:
            logger.debug(f"Extracting text from: {url}")
            
            # Download the webpage
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                logger.warning(f"Failed to download content from {url}")
                return ""
            
            # Extract text content
            text = trafilatura.extract(downloaded)
            
            if not text:
                logger.warning(f"No text extracted from {url}")
                return ""
            
            # Clean and validate text
            text = text.strip()
            
            if len(text) < 200:
                logger.warning(f"Extracted text too short from {url}: {len(text)} characters")
                return ""
            
            logger.debug(f"Successfully extracted {len(text)} characters from {url}")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {url}: {str(e)}")
            return ""
    
    def validate_url(self, url):
        """Validate if URL is accessible"""
        try:
            response = self.session.head(url, timeout=10)
            return response.status_code == 200
        except:
            return False
