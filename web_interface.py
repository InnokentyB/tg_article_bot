"""
Web interface for monitoring and controlling the RSS processor
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import logging
import threading
import time
from datetime import datetime, timedelta

from config import Config
from db import DatabaseManager
from rss_parser import RSSParser
from categorizer import ArticleCategorizer
from review_generator import ReviewGenerator
from publisher import TelegramPublisher

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.secret_key = 'rss_processor_secret_key_change_in_production'
    
    # Initialize components
    config = Config()
    db = DatabaseManager()
    publisher = TelegramPublisher()
    
    @app.route('/')
    def dashboard():
        """Main dashboard"""
        try:
            # Get statistics
            stats = db.get_statistics()
            
            # Get recent articles
            recent_articles = db.get_articles(limit=10)
            
            # Get unpublished articles
            unpublished = db.get_unpublished_articles(limit=5)
            
            return render_template('index.html', 
                                 stats=stats, 
                                 recent_articles=recent_articles,
                                 unpublished=unpublished,
                                 config=config)
                                 
        except Exception as e:
            logger.error(f"Error in dashboard: {str(e)}")
            flash(f"Error loading dashboard: {str(e)}", 'error')
            return render_template('index.html', stats={}, recent_articles=[], unpublished=[])
    
    @app.route('/articles')
    def articles():
        """Articles listing page"""
        try:
            page = int(request.args.get('page', 1))
            category = request.args.get('category', '')
            posted = request.args.get('posted', '')
            
            # Convert posted filter
            posted_filter = None
            if posted == 'true':
                posted_filter = True
            elif posted == 'false':
                posted_filter = False
            
            # Get articles
            articles_list = db.get_articles(
                limit=20, 
                category=category if category else None,
                posted=posted_filter
            )
            
            return render_template('articles.html', 
                                 articles=articles_list,
                                 current_category=category,
                                 current_posted=posted)
                                 
        except Exception as e:
            logger.error(f"Error in articles page: {str(e)}")
            flash(f"Error loading articles: {str(e)}", 'error')
            return render_template('articles.html', articles=[])
    
    @app.route('/process', methods=['POST'])
    def process_articles():
        """Trigger article processing"""
        try:
            def run_processing():
                from main import RSSProcessor
                processor = RSSProcessor()
                start_time = time.time()
                processed_count = processor.process_articles()
                processing_time = time.time() - start_time
                
                # Log the processing run
                db.log_processing(processed_count, 0, processing_time)
            
            # Run processing in background thread
            thread = threading.Thread(target=run_processing)
            thread.daemon = True
            thread.start()
            
            flash('Article processing started in background', 'info')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            logger.error(f"Error starting processing: {str(e)}")
            flash(f"Error starting processing: {str(e)}", 'error')
            return redirect(url_for('dashboard'))
    
    @app.route('/publish/<int:article_id>', methods=['POST'])
    def publish_article(article_id):
        """Publish specific article to Telegram"""
        try:
            article = db.get_article_by_id(article_id)
            if not article:
                flash('Article not found', 'error')
                return redirect(url_for('articles'))
            
            if article['posted']:
                flash('Article already published', 'warning')
                return redirect(url_for('articles'))
            
            success = publisher.publish_article(article)
            if success:
                db.mark_as_posted(article_id)
                flash('Article published successfully', 'success')
            else:
                flash('Failed to publish article', 'error')
            
            return redirect(url_for('articles'))
            
        except Exception as e:
            logger.error(f"Error publishing article: {str(e)}")
            flash(f"Error publishing article: {str(e)}", 'error')
            return redirect(url_for('articles'))
    
    @app.route('/test_telegram', methods=['POST'])
    def test_telegram():
        """Test Telegram configuration"""
        try:
            success = publisher.send_test_message()
            if success:
                flash('Test message sent successfully', 'success')
            else:
                flash('Failed to send test message', 'error')
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            logger.error(f"Error testing Telegram: {str(e)}")
            flash(f"Error testing Telegram: {str(e)}", 'error')
            return redirect(url_for('dashboard'))
    
    @app.route('/api/stats')
    def api_stats():
        """API endpoint for statistics"""
        try:
            stats = db.get_statistics()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error in API stats: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/validate_config')
    def api_validate_config():
        """API endpoint to validate configuration"""
        try:
            # Validate Telegram
            telegram_valid, telegram_msg = publisher.validate_configuration()
            
            # Validate OpenAI (basic check)
            openai_valid = bool(config.OPENAI_API_KEY)
            openai_msg = "OpenAI API key configured" if openai_valid else "OpenAI API key not configured"
            
            # Validate RSS
            rss_valid = bool(config.RSS_URL)
            rss_msg = f"RSS URL configured: {config.RSS_URL}" if rss_valid else "RSS URL not configured"
            
            return jsonify({
                'telegram': {'valid': telegram_valid, 'message': telegram_msg},
                'openai': {'valid': openai_valid, 'message': openai_msg},
                'rss': {'valid': rss_valid, 'message': rss_msg}
            })
            
        except Exception as e:
            logger.error(f"Error validating config: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/cleanup', methods=['POST'])
    def cleanup_articles():
        """Clean up old articles"""
        try:
            days = int(request.form.get('days', 30))
            deleted_count = db.cleanup_old_articles(days)
            flash(f'Cleaned up {deleted_count} old articles', 'info')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")
            flash(f"Error in cleanup: {str(e)}", 'error')
            return redirect(url_for('dashboard'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
