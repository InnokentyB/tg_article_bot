#!/usr/bin/env python3
"""
Main entry point for the RSS Article Processing System
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import time

from config import Config
from db import DatabaseManager
from rss_parser import RSSParser
from categorizer import ArticleCategorizer
from review_generator import ReviewGenerator
from publisher import TelegramPublisher
from web_interface import create_app
from scheduler import ArticleScheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rss_processor.log')
    ]
)

logger = logging.getLogger(__name__)

class RSSProcessor:
    def __init__(self):
        self.config = Config()
        self.db = DatabaseManager()
        self.rss_parser = RSSParser()
        self.categorizer = ArticleCategorizer()
        self.review_generator = ReviewGenerator()
        self.publisher = TelegramPublisher()
        
    def process_articles(self):
        """Main processing pipeline for articles"""
        try:
            logger.info("Starting article processing pipeline")
            
            # Parse RSS feeds
            articles = self.rss_parser.fetch_articles(self.config.RSS_URL)
            logger.info(f"Fetched {len(articles)} articles from RSS")
            
            processed_count = 0
            
            for article in articles:
                try:
                    # Check if article already exists
                    if self.db.article_exists(article['url']):
                        logger.debug(f"Article already exists: {article['title']}")
                        continue
                    
                    # Stage 1: Tag-based filtering
                    if not self.categorizer.filter_by_tags(article, self.config.ALLOWED_TAGS):
                        logger.debug(f"Article filtered out by tags: {article['title']}")
                        continue
                    
                    # Stage 2: Content-based categorization
                    category = self.categorizer.categorize_by_content(article['text'])
                    if not category or category == 'irrelevant':
                        logger.debug(f"Article filtered out by content: {article['title']}")
                        continue
                    
                    article['category'] = category
                    
                    # Generate review
                    review = self.review_generator.generate_review(article['text'], article['title'])
                    article['summary'] = review
                    
                    # Save to database
                    article_id = self.db.save_article(article)
                    logger.info(f"Saved article: {article['title']} (ID: {article_id})")
                    
                    # Publish to Telegram
                    if self.config.AUTO_PUBLISH:
                        success = self.publisher.publish_article(article)
                        if success:
                            self.db.mark_as_posted(article_id)
                            logger.info(f"Published article to Telegram: {article['title']}")
                        else:
                            logger.error(f"Failed to publish article: {article['title']}")
                    
                    processed_count += 1
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing article {article.get('title', 'Unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Processing complete. Processed {processed_count} new articles")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error in processing pipeline: {str(e)}")
            return 0

def run_web_interface():
    """Run the web interface"""
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)

def run_scheduled_processing():
    """Run scheduled article processing"""
    processor = RSSProcessor()
    scheduler = ArticleScheduler(processor)
    scheduler.start()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "web":
            logger.info("Starting web interface")
            run_web_interface()
        elif sys.argv[1] == "process":
            logger.info("Running one-time processing")
            processor = RSSProcessor()
            processor.process_articles()
        elif sys.argv[1] == "schedule":
            logger.info("Starting scheduled processing")
            run_scheduled_processing()
        else:
            print("Usage: python main.py [web|process|schedule]")
    else:
        # Default: run web interface
        logger.info("Starting web interface (default)")
        run_web_interface()
