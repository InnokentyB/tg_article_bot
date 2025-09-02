"""
Text extraction from URLs and content processing
"""
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from readability.readability import Document
import re

logger = logging.getLogger(__name__)

class TextExtractor:
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False
    
    async def extract_from_url(self, url: str) -> Optional[Dict[str, Optional[str]]]:
        """Extract article content from URL"""
        if not self.is_valid_url(url):
            logger.error(f"Invalid URL: {url}")
            return None
        
        try:
            if not self.session:
                raise RuntimeError("HTTP session not initialized")
            
            logger.info(f"Starting extraction from URL: {url}")
            
            async with self.session.get(url) as response:
                logger.info(f"HTTP response status: {response.status} for URL: {url}")
                
                if response.status != 200:
                    logger.error(f"HTTP {response.status} for URL: {url}")
                    return None
                
                html_content = await response.text()
                logger.info(f"Downloaded HTML content length: {len(html_content)} characters")

                # Check for common blocking patterns
                if any(blocked in html_content.lower() for blocked in ['captcha', 'blocked', 'access denied', 'forbidden', 'cloudflare']):
                    logger.warning(f"Site appears to be blocking requests: {url}")
                    raise RuntimeError("Site appears to be blocking automated requests")

                # Check content length
                if len(html_content) < 1000:
                    logger.warning(f"Content too short, possible blocking: {len(html_content)} chars")
                    raise RuntimeError("Content too short, site may be blocking requests")

                # Enhanced text extraction with multiple methods
                # Method 1: Use readability for main content
                logger.info("Using readability for text extraction")
                doc = Document(html_content)
                title = doc.title()
                readability_content = doc.summary()
                logger.info(f"Readability extracted title: {title[:100] if title else 'None'}")
                logger.info(f"Readability content length: {len(readability_content) if readability_content else 0}")

                # Method 2: Try trafilatura for better quality (with fallback)
                trafilatura_text = None
                try:
                    import trafilatura
                    logger.info("Trying trafilatura extraction")
                    trafilatura_text = trafilatura.extract(html_content, include_comments=False, include_tables=True)
                    logger.info(f"Trafilatura extracted text length: {len(trafilatura_text) if trafilatura_text else 0}")
                except ImportError:
                    logger.warning("trafilatura not available, using readability only")
                except Exception as e:
                    logger.warning(f"trafilatura extraction failed: {e}")

                # Choose better extraction result
                if trafilatura_text and len(trafilatura_text) > len(readability_content):
                    content = trafilatura_text
                    text = content
                    logger.info("Using trafilatura result (better quality)")
                else:
                    # Parse readability content with BeautifulSoup
                    logger.info("Using readability result with BeautifulSoup parsing")
                    soup = BeautifulSoup(readability_content, 'html.parser')
                    text = soup.get_text(strip=True, separator=' ')

                logger.info(f"Final extracted text length: {len(text) if text else 0}")

                # Validate extracted text
                if not text or len(text.strip()) < 100:
                    logger.warning(f"Extracted text too short: {len(text)} chars")
                    raise RuntimeError("Failed to extract meaningful text from the page")
                
                # Enhanced text cleaning  
                logger.info("Cleaning extracted text")
                text = self.clean_text(text)
                logger.info(f"Text after cleaning length: {len(text)}")
                
                # Extract source from URL
                parsed_url = urlparse(url)
                source = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                # Try to extract author and keywords from meta tags
                soup_full = BeautifulSoup(html_content, 'html.parser')
                author = self.extract_author(soup_full)
                keywords = self.extract_keywords_from_meta(soup_full)
                
                logger.info(f"Extraction successful for {url}: title={title[:50] if title else 'None'}, text_length={len(text)}, author={author}")
                
                return {
                    'title': title.strip() if title else None,
                    'text': text,
                    'source': source,
                    'author': author,
                    'keywords': keywords,
                    'original_link': url
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout extracting from URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting from URL {url}: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            return None
    
    def extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author from HTML meta tags"""
        # Common meta tag patterns for author
        author_selectors = [
            'meta[name="author"]',
            'meta[property="article:author"]',
            'meta[name="article:author"]',
            '.author',
            '.byline',
            '[rel="author"]'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    content = element.get('content')
                    author = content.strip() if content else ''
                else:
                    author = element.get_text(strip=True)
                
                if author and len(author) < 100:  # Reasonable author name length
                    return author
        
        return None
    
    def extract_keywords_from_meta(self, soup: BeautifulSoup) -> list:
        """Extract keywords from HTML meta tags"""
        keywords = []
        
        # Look for meta keywords tag
        meta_keywords = soup.select_one('meta[name="keywords"]')
        if meta_keywords:
            content = meta_keywords.get('content', '')
            if content:
                # Split by comma and clean up
                keywords.extend([kw.strip() for kw in content.split(',') if kw.strip()])
        
        # Also look for Habr-specific tags and hubs in meta or structured data
        # Try to find article tags/hubs in the page content
        tag_elements = soup.select('.tm-tags__item, .hub-link, .post__tag')
        for elem in tag_elements:
            tag_text = elem.get_text(strip=True)
            if tag_text and len(tag_text) < 50:  # Reasonable tag length
                keywords.append(tag_text)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
        
        return unique_keywords[:15]  # Limit to 15 keywords
    
    def clean_text(self, text: str) -> str:
        """Enhanced text cleaning with better quality"""
        if not text:
            return ""
        
        # Remove common noise patterns
        noise_patterns = [
            r'(Реклама|Комментарии|Поделиться|Подписаться|Войти|Регистрация)',
            r'(Advertisement|Comments|Share|Subscribe|Login|Register)',
            r'(Читать далее|Read more|Continue reading)',
            r'(Источник:|Source:|Via:|От:)',
            r'(Cookie|cookies|Согласие|Privacy)',
            r'(JavaScript|JS|включите|enable)',
            r'(\d+\s*(мин|минут|min|minutes)\s*(чтения|read))',
            r'(Теги:|Tags:|Метки:)',
            r'(Нравится|Like|\d+\s*👍|\d+\s*❤️)',
            r'Subscribe to.*?newsletter',
            r'Click here to.*?',
            r'Read more.*?'
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace and newlines
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove very short fragments (likely navigation)
        sentences = text.split('.')
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        if meaningful_sentences:
            text = '. '.join(meaningful_sentences)
        
        return text.strip()
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate simple summary from text"""
        if len(text) <= max_length:
            return text
        
        # Try to break at sentence boundary
        sentences = text.split('.')
        summary = ""
        
        for sentence in sentences:
            if len(summary + sentence + ".") <= max_length:
                summary += sentence + "."
            else:
                break
        
        if not summary:
            # Fallback to character limit
            summary = text[:max_length-3] + "..."
        
        return summary.strip()