"""
Scheduler for automated article processing
"""
import schedule
import time
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

class ArticleScheduler:
    def __init__(self, processor):
        self.processor = processor
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        
        # Schedule processing every 2 hours
        schedule.every(2).hours.do(self._run_processing)
        
        # Schedule daily cleanup at 2 AM
        schedule.every().day.at("02:00").do(self._run_cleanup)
        
        # Start scheduler thread
        self.thread = threading.Thread(target=self._scheduler_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Article scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("Article scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(60)
    
    def _run_processing(self):
        """Run article processing"""
        try:
            logger.info("Starting scheduled article processing")
            start_time = time.time()
            
            processed_count = self.processor.process_articles()
            
            processing_time = time.time() - start_time
            logger.info(f"Scheduled processing completed: {processed_count} articles processed in {processing_time:.2f} seconds")
            
            # Log the processing run
            self.processor.db.log_processing(processed_count, 0, processing_time)
            
        except Exception as e:
            logger.error(f"Error in scheduled processing: {str(e)}")
            # Log the error
            self.processor.db.log_processing(0, 0, 0, 'error', str(e))
    
    def _run_cleanup(self):
        """Run database cleanup"""
        try:
            logger.info("Starting scheduled cleanup")
            deleted_count = self.processor.db.cleanup_old_articles(30)
            logger.info(f"Cleanup completed: removed {deleted_count} old articles")
            
        except Exception as e:
            logger.error(f"Error in scheduled cleanup: {str(e)}")
