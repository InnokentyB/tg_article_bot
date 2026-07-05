#!/usr/bin/env python3
"""
Script to run the Telegram bot with proper environment loading
"""
import asyncio
import logging
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('article_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the bot"""
    try:
        from telegram_bot import ArticleBot
        from config import BotConfig
        
        # Validate configuration
        if not BotConfig.validate_article_bot():
            logger.error("❌ Invalid bot configuration. Please check your .env file.")
            logger.error(f"Configuration: {BotConfig.get_bot_info()}")
            return
        
        logger.info("✅ Bot configuration validated successfully")
        logger.info(f"Configuration: {BotConfig.get_bot_info()}")
        
        # Create and initialize bot
        bot = ArticleBot()
        await bot.initialize()
        
        logger.info("🚀 Starting bot...")
        logger.info("📱 Bot is now running. Press Ctrl+C to stop.")
        
        # Start polling
        await bot.dp.start_polling(bot.bot)
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error running bot: {e}")
        raise
    finally:
        try:
            await bot.shutdown()
            logger.info("✅ Bot shutdown completed")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
