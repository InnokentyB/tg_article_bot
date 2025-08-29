#!/usr/bin/env python3
"""
Простой тестовый Telegram бот без тяжелых ML моделей
"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from database import DatabaseManager
from text_extractor import TextExtractor
from article_categorizer import ArticleCategorizer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleArticleBot:
    def __init__(self):
        self.token = os.getenv('ARTICLE_BOT_TOKEN')
        if not self.token:
            raise ValueError("ARTICLE_BOT_TOKEN environment variable is required")
        
        self.bot = Bot(token=self.token)
        storage = MemoryStorage()
        self.dp = Dispatcher(storage=storage)
        self.db = DatabaseManager()
        self.text_extractor = TextExtractor()
        self.categorizer = ArticleCategorizer()
        
        # Register handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup message handlers"""
        self.dp.message(Command('start'))(self.cmd_start)
        self.dp.message(Command('help'))(self.cmd_help)
        self.dp.message(Command('stats'))(self.cmd_stats)
        self.dp.message()(self.process_message)
    
    async def initialize(self):
        """Initialize all components"""
        await self.db.initialize()
        await self.text_extractor.initialize()
        
        # Force delete webhook to ensure polling works
        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted successfully")
        except Exception as e:
            logger.warning(f"Failed to delete webhook: {e}")
        logger.info("Simple bot initialized successfully")
    
    async def shutdown(self):
        """Shutdown all components"""
        await self.db.close()
        await self.text_extractor.close()
        await self.bot.session.close()
        logger.info("Simple bot shutdown completed")
    
    async def cmd_start(self, message: Message):
        """Handle /start command"""
        user = message.from_user
        if user:
            await self.db.save_user(
                telegram_user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
        
        welcome_text = """
🤖 Простой Article Management Bot

Отправьте мне:
• Текст статьи (минимум 50 символов)
• Ссылку на статью

Команды:
/help - Справка
/stats - Статистика
        """
        await message.answer(welcome_text.strip())
    
    async def cmd_help(self, message: Message):
        """Handle /help command"""
        help_text = """
📖 Справка по использованию бота

1. Отправьте текст статьи (минимум 50 символов)
2. Или отправьте ссылку на статью
3. Бот сохранит статью и предложит добавить категории

Функции:
• Автоматическое извлечение текста из ссылок
• Базовая категоризация
• Поиск дубликатов
• Статистика
        """
        await message.answer(help_text.strip())
    
    async def cmd_stats(self, message: Message):
        """Handle /stats command"""
        try:
            user_id = message.from_user.id
            user_articles = await self.db.get_articles(user_id=user_id, limit=100)
            total_articles = await self.db.get_articles_count()
            
            stats_text = f"""
📊 Статистика

Ваши статьи: {len(user_articles)}
Всего статей в системе: {total_articles}
            """
            await message.answer(stats_text.strip())
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await message.answer("❌ Ошибка при получении статистики")
    
    async def process_message(self, message: Message):
        """Process incoming messages"""
        try:
            text = message.text
            if not text:
                await message.answer("❌ Отправьте текст или ссылку на статью")
                return
            
            # Check if it's a URL
            if text.startswith(('http://', 'https://')):
                await message.answer("🔍 Извлекаю текст из ссылки...")
                extracted_text = await self.text_extractor.extract_text(text)
                if extracted_text:
                    await self.save_article(message, extracted_text, text)
                else:
                    await message.answer("❌ Не удалось извлечь текст из ссылки")
            else:
                # Check minimum length
                if len(text) < 50:
                    await message.answer("❌ Текст должен содержать минимум 50 символов")
                    return
                
                await self.save_article(message, text)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await message.answer("❌ Произошла ошибка при обработке сообщения")
    
    async def save_article(self, message: Message, text: str, source: str = None):
        """Save article to database"""
        try:
            user_id = message.from_user.id
            
            # Basic categorization
            categories = self.categorizer.categorize_text(text)
            
            # Save article
            article_id = await self.db.save_article(
                title=text[:100] + "..." if len(text) > 100 else text,
                text=text,
                source=source,
                telegram_user_id=user_id,
                categories_auto=categories
            )
            
            response = f"""
✅ Статья сохранена!

ID: {article_id}
Категории: {', '.join(categories) if categories else 'Не определены'}
            """
            await message.answer(response.strip())
            
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            await message.answer("❌ Ошибка при сохранении статьи")
    
    async def start_polling(self):
        """Start the bot"""
        await self.initialize()
        logger.info("Starting simple bot polling...")
        await self.dp.start_polling(self.bot)

async def main():
    """Main function"""
    logger.info("Starting Simple Telegram bot...")
    
    # Check required environment variables
    if not os.getenv('DATABASE_URL'):
        logger.error("DATABASE_URL environment variable is required")
        return
    
    if not os.getenv('ARTICLE_BOT_TOKEN'):
        logger.error("ARTICLE_BOT_TOKEN environment variable is required")
        return
    
    bot = SimpleArticleBot()
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
