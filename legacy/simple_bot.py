"""
Simple version to test just the Telegram bot
"""
import asyncio
import logging
import os
from telegram_bot import ArticleBot
from config import BotConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Run only the Telegram bot"""
    logger.info("Starting Telegram bot...")
    
    # Check required environment variables
    if not os.getenv('DATABASE_URL'):
        logger.error("DATABASE_URL environment variable is required")
        return
    
    if not BotConfig.validate_article_bot():
        logger.error("Bot configuration incomplete. Check ARTICLE_BOT_TOKEN and DATABASE_URL")
        logger.info(f"Configuration status: {BotConfig.get_bot_info()}")
        return
    
    bot = ArticleBot()
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(main())