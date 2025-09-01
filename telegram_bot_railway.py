"""
Telegram bot integrated with Railway API
"""
import asyncio
import logging
import os
from typing import Optional, Dict, Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config_railway import RailwayConfig
from railway_api_client import RailwayAPIClient
from text_extractor import TextExtractor

logger = logging.getLogger(__name__)

class ArticleStates(StatesGroup):
    waiting_for_categories = State()

class RailwayArticleBot:
    """Telegram bot integrated with Railway API"""
    
    def __init__(self):
        self.config = RailwayConfig()
        
        # Validate configuration
        if not self.config.validate_railway_bot():
            raise ValueError("Invalid Railway bot configuration")
        
        self.token = self.config.ARTICLE_BOT_TOKEN
        self.bot = Bot(token=self.token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        
        # Initialize components
        self.text_extractor = TextExtractor()
        self.railway_client = RailwayAPIClient()
        
        # Register handlers
        self.setup_handlers()
        
        logger.info("Railway bot initialized successfully")
    
    def setup_handlers(self):
        """Setup message handlers"""
        # Commands
        self.dp.message(Command('start'))(self.cmd_start)
        self.dp.message(Command('help'))(self.cmd_help)
        self.dp.message(Command('stats'))(self.cmd_stats)
        self.dp.message(Command('status'))(self.cmd_status)
        self.dp.message(Command('cancel'))(self.cmd_cancel)
        
        # FSM states
        self.dp.message(ArticleStates.waiting_for_categories)(self.process_categories)
        
        # General message handler
        self.dp.message()(self.process_message)
        
        # Callback handlers
        self.dp.callback_query(lambda c: c.data and c.data.startswith('add_categories:'))(self.callback_add_categories)
        self.dp.callback_query(lambda c: c.data and c.data.startswith('done:'))(self.callback_done)
        self.dp.callback_query(lambda c: c.data and c.data.startswith('stats:'))(self.callback_show_stats)
    
    async def initialize(self):
        """Initialize bot components"""
        await self.text_extractor.initialize()
        
        # Test Railway API connection
        connection_status = await self.railway_client.test_connection()
        logger.info(f"Railway API connection status: {connection_status}")
        
        # Force delete webhook
        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted successfully")
        except Exception as e:
            logger.warning(f"Failed to delete webhook: {e}")
        
        logger.info("Railway bot initialized successfully")
    
    async def shutdown(self):
        """Shutdown bot components"""
        await self.text_extractor.close()
        await self.bot.session.close()
        logger.info("Railway bot shutdown completed")
    
    async def cmd_start(self, message: Message):
        """Handle /start command"""
        user = message.from_user
        
        # Create/update user in Railway API
        user_data = {
            'telegram_user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        try:
            await self.railway_client.create_user(user_data)
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
        
        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "🤖 Я бот для управления статьями, интегрированный с Railway API.\n\n"
            "📝 Отправьте мне ссылку на статью, и я:\n"
            "• Извлеку текст и заголовок\n"
            "• Сохраню в базу данных\n"
            "• Предложу категории\n\n"
            "🔧 Доступные команды:\n"
            "/help - показать справку\n"
            "/stats - статистика\n"
            "/status - статус API\n"
            "/cancel - отменить текущую операцию"
        )
        
        await message.answer(welcome_text)
    
    async def cmd_help(self, message: Message):
        """Handle /help command"""
        help_text = (
            "📚 **Справка по боту**\n\n"
            "🔗 **Отправка статьи:**\n"
            "Просто отправьте ссылку на статью, и я автоматически:\n"
            "• Извлеку содержимое\n"
            "• Сохраню в базу\n"
            "• Предложу категории\n\n"
            "📊 **Команды:**\n"
            "/start - начать работу\n"
            "/stats - показать статистику\n"
            "/status - проверить статус API\n"
            "/cancel - отменить операцию\n\n"
            "🏷️ **Категории:**\n"
            "После сохранения статьи вы можете:\n"
            "• Выбрать предложенные категории\n"
            "• Добавить свои категории\n"
            "• Просмотреть сохраненные статьи\n\n"
            "💡 **Советы:**\n"
            "• Поддерживаются большинство новостных сайтов\n"
            "• Категории помогают организовать статьи\n"
            "• Все данные сохраняются в Railway"
        )
        
        await message.answer(help_text, parse_mode='Markdown')
    
    async def cmd_stats(self, message: Message):
        """Handle /stats command"""
        try:
            stats = await self.railway_client.get_statistics()
            
            if stats:
                stats_text = (
                    "📊 **Статистика Railway API**\n\n"
                    f"📝 Всего статей: {stats.get('total_articles', 'N/A')}\n"
                    f"👥 Пользователей: {stats.get('total_users', 'N/A')}\n"
                    f"🏷️ Категорий: {stats.get('total_categories', 'N/A')}\n"
                    f"📅 Последняя статья: {stats.get('last_article_date', 'N/A')}\n\n"
                    f"🔄 Статус API: ✅ Работает"
                )
            else:
                stats_text = "❌ Не удалось получить статистику"
                
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            stats_text = "❌ Ошибка при получении статистики"
        
        await message.answer(stats_text, parse_mode='Markdown')
    
    async def cmd_status(self, message: Message):
        """Handle /status command"""
        try:
            status = await self.railway_client.test_connection()
            
            if status['connected']:
                status_text = (
                    "🟢 **Статус Railway API**\n\n"
                    f"🌐 API URL: `{status['api_url']}`\n"
                    f"✅ Health Check: Работает\n"
                    f"🏷️ Категории: {'Работает' if status['categories_endpoint'] else 'Ошибка'}\n"
                    f"📊 Статистика: {'Работает' if status['stats_endpoint'] else 'Ошибка'}\n"
                    f"🕐 Проверено: {status['timestamp']}"
                )
            else:
                status_text = (
                    "🔴 **Статус Railway API**\n\n"
                    f"❌ Соединение не установлено\n"
                    f"🌐 API URL: `{status['api_url']}`\n"
                    f"⚠️ Ошибка: {status.get('error', 'Неизвестно')}\n"
                    f"🕐 Проверено: {status['timestamp']}"
                )
                
        except Exception as e:
            logger.error(f"Failed to check status: {e}")
            status_text = "❌ Ошибка при проверке статуса"
        
        await message.answer(status_text, parse_mode='Markdown')
    
    async def cmd_cancel(self, message: Message, state: FSMContext):
        """Handle /cancel command"""
        current_state = await state.get_state()
        if current_state:
            await state.clear()
            await message.answer("✅ Операция отменена")
        else:
            await message.answer("❌ Нет активных операций для отмены")
    
    async def process_message(self, message: Message, state: FSMContext):
        """Process incoming messages"""
        # Check if we're waiting for categories
        current_state = await state.get_state()
        if current_state == ArticleStates.waiting_for_categories:
            return
        
        # Check if message contains a URL
        if message.entities:
            for entity in message.entities:
                if entity.type == "url":
                    url = message.text[entity.offset:entity.offset + entity.length]
                    await self.process_article_url(message, url)
                    return
        
        # Check if message text looks like a URL
        if message.text and ('http://' in message.text or 'https://' in message.text):
            await self.process_article_url(message, message.text)
            return
        
        # If no URL found, show help
        await message.answer(
            "🔗 Отправьте мне ссылку на статью для обработки.\n"
            "Используйте /help для получения справки."
        )
    
    async def process_article_url(self, message: Message, url: str):
        """Process article URL and extract content"""
        await message.answer("🔄 Обрабатываю статью...")
        
        try:
            # Extract text from URL
            extracted_data = await self.text_extractor.extract_from_url(url)
            
            if not extracted_data or not extracted_data.get('text'):
                await message.answer("❌ Не удалось извлечь текст из статьи")
                return
            
            # Prepare article data for Railway API
            article_data = {
                'title': extracted_data.get('title', 'Без заголовка'),
                'text': extracted_data['text'],
                'summary': extracted_data.get('summary', ''),
                'source': url,
                'original_link': url,
                'telegram_user_id': message.from_user.id,
                'language': extracted_data.get('language', 'ru'),
                'categories_auto': extracted_data.get('categories', [])
            }
            
            # Save article to Railway API
            saved_article = await self.railway_client.create_article(article_data)
            
            if saved_article:
                # Show success message with categories
                await self.show_article_saved(message, saved_article, extracted_data.get('categories', []))
            else:
                await message.answer("❌ Не удалось сохранить статью в Railway API")
                
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            await message.answer("❌ Ошибка при обработке статьи")
    
    async def show_article_saved(self, message: Message, article: Dict[str, Any], auto_categories: list):
        """Show article saved successfully with category options"""
        # Get available categories from Railway API
        try:
            available_categories = await self.railway_client.get_categories()
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            available_categories = []
        
        # Combine auto categories with available ones
        all_categories = list(set(auto_categories + available_categories))
        
        # Create keyboard for category selection
        builder = InlineKeyboardBuilder()
        
        # Add auto categories first
        for category in auto_categories[:5]:  # Limit to 5 categories
            builder.button(
                text=f"✅ {category}",
                callback_data=f"add_categories:{article['id']}:{category}"
            )
        
        # Add other available categories
        for category in available_categories[:10]:  # Limit to 10 total
            if category not in auto_categories:
                builder.button(
                    text=f"🏷️ {category}",
                    callback_data=f"add_categories:{article['id']}:{category}"
                )
        
        builder.button(text="✅ Готово", callback_data=f"done:{article['id']}")
        
        # Adjust layout
        builder.adjust(2)
        
        success_text = (
            f"✅ **Статья сохранена!**\n\n"
            f"📝 **{article['title']}**\n"
            f"🔗 Источник: {article['source']}\n"
            f"📊 ID: `{article['id']}`\n\n"
            f"🏷️ **Выберите категории:**\n"
            f"• Автоматически определенные: {', '.join(auto_categories[:3])}\n"
            f"• Доступные: {', '.join(available_categories[:5])}\n\n"
            f"💡 Нажмите на категории для добавления"
        )
        
        await message.answer(success_text, reply_markup=builder.as_markup(), parse_mode='Markdown')
    
    async def process_categories(self, message: Message, state: FSMContext):
        """Process category input from user"""
        # This would handle manual category input
        # For now, just show help
        await message.answer(
            "🏷️ Используйте кнопки выше для выбора категорий\n"
            "Или нажмите '✅ Готово' для завершения"
        )
    
    async def callback_add_categories(self, callback: CallbackQuery):
        """Handle category selection callback"""
        try:
            data = callback.data.split(':')
            article_id = int(data[1])
            category = data[2]
            
            # Update article with selected category
            update_data = {
                'categories_user': [category]
            }
            
            updated_article = await self.railway_client.update_article(article_id, update_data)
            
            if updated_article:
                await callback.answer(f"✅ Категория '{category}' добавлена")
            else:
                await callback.answer("❌ Ошибка при добавлении категории")
                
        except Exception as e:
            logger.error(f"Error adding category: {e}")
            await callback.answer("❌ Ошибка при обработке")
    
    async def callback_done(self, callback: CallbackQuery):
        """Handle done callback"""
        try:
            data = callback.data.split(':')
            article_id = int(data[1])
            
            # Get final article data
            article = await self.railway_client.get_article(article_id)
            
            if article:
                final_text = (
                    f"🎉 **Статья полностью обработана!**\n\n"
                    f"📝 **{article['title']}**\n"
                    f"🔗 ID: `{article['id']}`\n"
                    f"🏷️ Категории: {', '.join(article.get('categories_user', []) + article.get('categories_auto', []))}\n\n"
                    f"💾 Данные сохранены в Railway API\n"
                    f"📊 Используйте /stats для просмотра статистики"
                )
            else:
                final_text = "✅ Обработка завершена"
            
            await callback.message.edit_text(final_text, parse_mode='Markdown')
            await callback.answer("✅ Готово!")
            
        except Exception as e:
            logger.error(f"Error in done callback: {e}")
            await callback.answer("❌ Ошибка при завершении")
    
    async def callback_show_stats(self, callback: CallbackQuery):
        """Handle stats callback"""
        try:
            stats = await self.railway_client.get_statistics()
            
            if stats:
                stats_text = (
                    "📊 **Статистика Railway API**\n\n"
                    f"📝 Всего статей: {stats.get('total_articles', 'N/A')}\n"
                    f"👥 Пользователей: {stats.get('total_users', 'N/A')}\n"
                    f"🏷️ Категорий: {stats.get('total_categories', 'N/A')}\n"
                    f"📅 Последняя статья: {stats.get('last_article_date', 'N/A')}"
                )
            else:
                stats_text = "❌ Не удалось получить статистику"
            
            await callback.message.edit_text(stats_text, parse_mode='Markdown')
            await callback.answer("📊 Статистика обновлена")
            
        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            await callback.answer("❌ Ошибка при получении статистики")
    
    async def run(self):
        """Run the bot"""
        try:
            await self.initialize()
            logger.info("Starting Railway bot...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            await self.shutdown()

async def main():
    """Main function"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        bot = RailwayArticleBot()
        await bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
