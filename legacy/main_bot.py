"""
Main entry point for the Telegram bot and API server
"""
import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
import uvicorn

from telegram_bot import ArticleBot
from api_server import app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('article_bot.log')
    ]
)

logger = logging.getLogger(__name__)

async def run_bot():
    """Run Telegram bot"""
    try:
        bot = ArticleBot()
        await bot.start_polling()
    except Exception as e:
        logger.error(f"Bot error: {e}")
        sys.exit(1)

def run_api():
    """Run FastAPI server"""
    try:
        uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
    except Exception as e:
        logger.error(f"API server error: {e}")
        sys.exit(1)

async def main():
    """Main function"""
    logger.info("Starting Article Management System...")
    
    # Check required environment variables
    required_vars = ['DATABASE_URL', 'TELEGRAM_BOT_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Create executor for running API server in separate thread
    executor = ThreadPoolExecutor(max_workers=1)
    
    # Start API server in background thread
    api_future = asyncio.get_event_loop().run_in_executor(executor, run_api)
    
    # Run bot in main thread
    bot_task = asyncio.create_task(run_bot())
    
    try:
        # Wait for both to complete (they should run indefinitely)
        await asyncio.gather(bot_task, api_future)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bot_task.cancel()
        executor.shutdown(wait=True)
    except Exception as e:
        logger.error(f"Main error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())