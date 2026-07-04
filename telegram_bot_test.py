"""
Telegram bot for article management - TEST VERSION
"""
import asyncio
import logging
import os
from typing import Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, MessageReactionUpdated, MessageReactionCountUpdated
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database import DatabaseManager
from text_extractor import TextExtractor
from article_categorizer import ArticleCategorizer
from advanced_categorizer import AdvancedCategorizer
from telegram_reactions import TelegramReactionsTracker
from external_source_tracker import ExternalSourceTracker

logger = logging.getLogger(__name__)

class ArticleStates(StatesGroup):
    waiting_for_categories = State()

class ArticleBotTest:
    def __init__(self):
        self.token = os.getenv('ARTICLE_BOT_TEST_TOKEN')
        if not self.token:
            raise ValueError("ARTICLE_BOT_TEST_TOKEN environment variable is required")
        
        self.bot = Bot(token=self.token)
        # Use memory storage for FSM
        storage = MemoryStorage()
        self.dp = Dispatcher(storage=storage)
        self.db = DatabaseManager()
        self.text_extractor = TextExtractor()
        self.categorizer = ArticleCategorizer()
        self.advanced_categorizer = AdvancedCategorizer()
        self.reactions_tracker = TelegramReactionsTracker(self.db)
        self.external_tracker = ExternalSourceTracker(self.db)
        
        # Register handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup message handlers - order matters!"""
        # Commands first
        self.dp.message(Command('start'))(self.cmd_start)
        self.dp.message(Command('help'))(self.cmd_help)
        self.dp.message(Command('stats'))(self.cmd_stats)
        self.dp.message(Command('cancel'))(self.cmd_cancel)
        
        # FSM states have priority over general message handler
        self.dp.message(ArticleStates.waiting_for_categories)(self.process_categories)
        
        # General message handler last
        self.dp.message()(self.process_message)
        
        # Callback handlers
        self.dp.callback_query(lambda c: c.data and c.data.startswith('add_categories:'))(self.callback_add_categories)
        self.dp.callback_query(lambda c: c.data and c.data.startswith('done:'))(self.callback_done)
        self.dp.callback_query(lambda c: c.data and c.data.startswith('stats:'))(self.callback_show_stats)
        self.dp.callback_query(lambda c: c.data and c.data.startswith('track_external:'))(self.callback_track_external)
        
        # Reaction handlers (requires bot to be admin in chat)
        self.dp.message_reaction()(self.handle_message_reaction)
        self.dp.message_reaction_count()(self.handle_message_reaction_count)
    
    async def initialize(self):
        """Initialize all components and force delete webhook"""
        await self.db.initialize()
        await self.text_extractor.initialize()
        await self.external_tracker.initialize()
        # Force delete webhook to ensure polling works
        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted successfully")
        except Exception as e:
            logger.warning(f"Failed to delete webhook: {e}")
        logger.info("Test Bot initialized successfully")
    
    async def shutdown(self):
        """Shutdown all components"""
        await self.db.close()
        await self.text_extractor.close()
        await self.external_tracker.close()
        await self.bot.session.close()
        logger.info("Test Bot shutdown completed")
    
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
        
        welcome_text = f"""
🤖 **Добро пожаловать в Article Storage Bot - ТЕСТОВАЯ ВЕРСИЯ!**

👋 Привет, {user.first_name if user else 'пользователь'}!

📰 Этот бот поможет вам:
• Сохранять статьи из интернета
• Автоматически категоризировать контент
• Анализировать и структурировать информацию
• Отслеживать статистику

🔬 **ТЕСТОВОЕ ОКРУЖЕНИЕ**
• Все данные сохраняются в тестовую базу
• Экспериментальные функции включены
• Расширенная диагностика

📝 **Как использовать:**
1. Отправьте ссылку на статью
2. Бот извлечет и проанализирует контент
3. Получите детальную категоризацию
4. Статья сохранится в базу данных

🔧 **Доступные команды:**
/start - Начать работу
/help - Справка
/stats - Статистика
/cancel - Отменить операцию

🚀 **Отправьте ссылку на статью для начала!**
        """
        
        # Create inline keyboard
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="📊 Статистика", 
            callback_data="stats:main"
        ))
        builder.add(types.InlineKeyboardButton(
            text="🔗 Отслеживание источников", 
            callback_data="track_external:main"
        ))
        builder.add(types.InlineKeyboardButton(
            text="🌐 Веб-админка", 
            url="https://tg-article-bot-api-production-12d6.up.railway.app"
        ))
        
        await message.answer(welcome_text, reply_markup=builder.as_markup())
    
    async def cmd_help(self, message: Message):
        """Handle /help command"""
        help_text = """
📚 **Справка по Article Storage Bot - ТЕСТОВАЯ ВЕРСИЯ**

🔬 **Особенности тестового окружения:**
• Расширенная диагностика
• Экспериментальные функции
• Подробные логи
• Тестовая база данных

📰 **Обработка статей:**
1. Отправьте URL статьи
2. Бот извлечет текст и метаданные
3. Выполнит многоуровневую категоризацию:
   • Базовая (rule-based)
   • AI категоризация (если доступна)
   • BART нейросетевая классификация
   • Тематическая кластеризация
4. Сохранит в базу данных
5. Покажет детальный анализ

🏷️ **Система категоризации:**
• Автоматическое определение языка
• Извлечение ключевых слов
• Определение основной темы
• Подкатегории и теги
• Оценка уверенности

📊 **Статистика и аналитика:**
• Количество сохраненных статей
• Популярные категории
• Активность пользователей
• Анализ источников

🔧 **Дополнительные функции:**
• Отслеживание реакций на сообщения
• Анализ внешних источников
• Проверка дубликатов
• Генерация отпечатков контента

❓ **Нужна помощь?** Обратитесь к администратору.
        """
        await message.answer(help_text)
    
    async def cmd_stats(self, message: Message):
        """Handle /stats command"""
        try:
            stats = await self.db.get_stats()
            
            stats_text = f"""
📊 **Статистика - ТЕСТОВАЯ ВЕРСИЯ**

📈 **Общая статистика:**
• Всего статей: {stats.get('total_articles', 0)}
• Уникальных пользователей: {stats.get('unique_users', 0)}
• Языков: {stats.get('languages_count', 0)}
• Средняя длина текста: {stats.get('avg_text_length', 0):.0f} символов
• Последняя статья: {stats.get('last_article_date', 'Нет данных')}

🏷️ **Категории:**
• Популярные категории: {', '.join(stats.get('top_categories', ['Нет данных']))}
• Всего категорий: {stats.get('categories_count', 0)}

👥 **Пользователи:**
• Активных пользователей: {stats.get('active_users', 0)}
• Новых пользователей сегодня: {stats.get('new_users_today', 0)}

🔬 **Тестовые метрики:**
• Время обработки: {stats.get('avg_processing_time', 0):.2f} сек
• Успешность извлечения: {stats.get('extraction_success_rate', 0):.1%}
• Точность категоризации: {stats.get('categorization_accuracy', 0):.1%}

📝 *Данные из тестовой базы данных*
            """
            
            # Create inline keyboard for detailed stats
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="📊 Детальная статистика", 
                callback_data="stats:detailed"
            ))
            builder.add(types.InlineKeyboardButton(
                text="🌐 Веб-админка", 
                url="https://tg-article-bot-api-production-12d6.up.railway.app"
            ))
            
            await message.answer(stats_text, reply_markup=builder.as_markup())
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await message.answer("❌ Ошибка при получении статистики")
    
    async def cmd_cancel(self, message: Message):
        """Handle /cancel command"""
        await message.answer("❌ Операция отменена")
    
    async def process_message(self, message: Message):
        """Process incoming messages"""
        if not message.text:
            return
        
        text = message.text.strip()
        
        # Check if it's a URL
        if text.startswith(('http://', 'https://')):
            await self.process_article_url(message, text)
        else:
            await message.answer(
                "🔗 Пожалуйста, отправьте ссылку на статью для обработки.\n\n"
                "Или используйте команды:\n"
                "/start - Начать работу\n"
                "/help - Справка\n"
                "/stats - Статистика"
            )
    
    async def process_article_url(self, message: Message, url: str):
        """Process article URL"""
        logger.info(f"Processing new message from user {message.from_user.id}: {url}...")
        
        # Send initial status message
        status_msg = await message.answer("🔄 Обрабатываю статью...")
        
        try:
            # Extract content
            await status_msg.edit_text("📖 Извлекаю контент...")
            content = await self.text_extractor.extract_from_url(url)
            
            if not content or not content.get('text'):
                await status_msg.edit_text("❌ Не удалось извлечь контент из статьи")
                return
            
            # Detect language and basic categorize
            await status_msg.edit_text("🏷️ Категоризирую контент...")
            language = self.categorizer.detect_language(content['text'])
            categories = self.categorizer.categorize_article(content['text'], content['title'])
            
            # Advanced categorization with OpenAI (if available)
            advanced_categories = None
            try:
                if self.advanced_categorizer.is_available():
                    await status_msg.edit_text("🤖 Выполняю углубленную категоризацию...")
                    advanced_categories = await self.advanced_categorizer.categorize_article(
                        content['text'], content['title'], language, content.get('keywords')
                    )
                    logger.info(f"Advanced categorization completed: {advanced_categories['primary_category']}")
            except Exception as e:
                logger.error(f"Advanced categorization failed: {e}")
            
            # Generate summary (use AI summary if available)
            summary = advanced_categories.get('summary') if advanced_categories else None
            if not summary:
                summary = content.get('summary') or self.text_extractor.generate_summary(content['text'])
            
            # Save article
            user_id = message.from_user.id if message.from_user else None
            article_id, _ = await self.db.save_article(
                title=content['title'],
                text=content['text'],
                summary=summary,
                source=content['source'],
                author=content['author'],
                original_link=url,
                categories_advanced=advanced_categories,
                language=language,
                telegram_user_id=user_id
            )
            
            # Update categories
            await self.db.update_article_categories(article_id, categories)
            
            # Success message with advanced categorization info
            success_text = f"✅ *Статья сохранена! - ТЕСТОВАЯ ВЕРСИЯ*\n\n"
            if content['title']:
                success_text += f"📰 *Заголовок:* {content['title'][:100]}...\n"
            
            # Show dual categorization if available
            if advanced_categories:
                success_text += "\n🤖 **AI Категоризация:**\n"
                
                # AI-based categorization
                ai_cat = advanced_categories.get('ai_categorization')
                if ai_cat:
                    success_text += f"🎯 *Категория:* {ai_cat.get('primary_category_label', 'Неизвестно')}\n"
                    if ai_cat.get('subcategories'):
                        success_text += f"📂 *Подкатегории:* {', '.join(ai_cat['subcategories'])}\n"
                    if ai_cat.get('keywords'):
                        success_text += f"🏷️ *Ключевые слова:* {', '.join(ai_cat['keywords'][:4])}\n"
                    success_text += f"🎲 *Уверенность:* {ai_cat.get('confidence', 0):.1%}\n"
                
                # Topic clustering
                topic_cat = advanced_categories.get('topic_clustering')
                if topic_cat:
                    success_text += "\n🔍 **Тематическая кластеризация:**\n"
                    success_text += f"📊 *Тема:* {topic_cat.get('topic_label', 'Неизвестно')}\n"
                    if topic_cat.get('topic_keywords'):
                        success_text += f"🏷️ *Ключевые термины:* {', '.join(topic_cat['topic_keywords'][:4])}\n"
                    success_text += f"📈 *Уверенность:* {topic_cat.get('confidence', 0):.1%}\n"
                
                # BART categorization  
                bart_cat = advanced_categories.get('bart_categorization')
                if bart_cat:
                    method = bart_cat.get('method', '')
                    if method == 'bart_disabled':
                        success_text += "\n🤖 **BART Классификация:** ⚠️ Недоступна\n"
                        success_text += "📋 *Статус:* Transformers библиотека не установлена\n"
                    elif method == 'rule_based_classification':
                        success_text += "\n🔧 **Rule-based Классификация:**\n"
                        success_text += f"🎯 *Категория:* {bart_cat.get('primary_category', 'Неизвестно')}\n"
                        if bart_cat.get('matched_keywords'):
                            success_text += f"🔑 *Найденные термины:* {', '.join(bart_cat['matched_keywords'][:3])}\n"
                        success_text += f"🎲 *Уверенность:* {bart_cat.get('confidence', 0):.1%}\n"
                    elif method == 'bart_zero_shot':
                        success_text += "\n🤖 **BART Классификация:**\n"
                        success_text += f"🎯 *Категория:* {bart_cat.get('primary_category', 'Неизвестно')}\n"
                        if bart_cat.get('categories'):
                            top_cats = [f"{cat['category']} ({cat['confidence']:.1%})" for cat in bart_cat['categories'][:2]]
                            success_text += f"📋 *Топ категории:* {', '.join(top_cats)}\n"
                        success_text += f"🎲 *Уверенность:* {bart_cat.get('confidence', 0):.1%}\n"
                    else:
                        success_text += f"\n🔧 **Альтернативная классификация:**\n"
                        success_text += f"🎯 *Категория:* {bart_cat.get('primary_category', 'Неизвестно')}\n"
                        success_text += f"🎲 *Уверенность:* {bart_cat.get('confidence', 0):.1%}\n"
                
                # Fallback to legacy format
                if not ai_cat and not topic_cat and not bart_cat:
                    success_text += f"🎯 *Основная категория:* {advanced_categories.get('primary_category_label', 'Неизвестно')}\n"
                    if advanced_categories.get('subcategories'):
                        success_text += f"📂 *Подкатегории:* {', '.join(advanced_categories['subcategories'])}\n"
                    if advanced_categories.get('keywords'):
                        success_text += f"🏷️ *Ключевые слова:* {', '.join(advanced_categories['keywords'][:5])}\n"
                    success_text += f"🎲 *Уверенность:* {advanced_categories.get('confidence', 0):.1%}\n"
            else:
                # Basic categorization
                success_text += f"🏷️ *Категория:* {categories[0] if categories else 'Неизвестно'}\n"
                if len(categories) > 1:
                    success_text += f"📂 *Дополнительные:* {', '.join(categories[1:3])}\n"
            
            # Add basic info
            success_text += f"\n📏 *Длина текста:* {len(content['text'])} символов\n"
            success_text += f"🌐 *Язык:* {language}\n"
            success_text += f"📅 *Дата:* {content.get('date', 'Неизвестно')}\n"
            success_text += f"👤 *Автор:* {content.get('author', 'Неизвестно')}\n"
            
            # Add test environment indicator
            success_text += f"\n🔬 *ТЕСТОВАЯ ВЕРСИЯ*\n"
            success_text += f"📊 ID статьи: {article_id}\n"
            success_text += f"💾 Сохранено в тестовую базу\n"
            
            # Create inline keyboard
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="📊 Статистика", 
                callback_data="stats:main"
            ))
            builder.add(types.InlineKeyboardButton(
                text="🌐 Веб-админка", 
                url="https://tg-article-bot-api-production-12d6.up.railway.app"
            ))
            
            await status_msg.edit_text(success_text, reply_markup=builder.as_markup())
            
        except Exception as e:
            logger.error(f"Error processing URL: {e}")
            await status_msg.edit_text(f"❌ Ошибка при обработке статьи: {str(e)}")
    
    async def process_categories(self, message: Message, state: FSMContext):
        """Process categories input"""
        # Implementation for category processing
        pass
    
    async def callback_add_categories(self, callback: CallbackQuery, state: FSMContext):
        """Handle add categories callback"""
        # Implementation for adding categories
        pass
    
    async def callback_done(self, callback: CallbackQuery, state: FSMContext):
        """Handle done callback"""
        # Implementation for done action
        pass
    
    async def callback_show_stats(self, callback: CallbackQuery):
        """Handle stats callback"""
        # Implementation for showing stats
        pass
    
    async def callback_track_external(self, callback: CallbackQuery):
        """Handle track external callback"""
        # Implementation for tracking external sources
        pass
    
    async def handle_message_reaction(self, event: MessageReactionUpdated):
        """Handle message reactions"""
        # Implementation for message reactions
        pass
    
    async def handle_message_reaction_count(self, event: MessageReactionCountUpdated):
        """Handle message reaction count updates"""
        # Implementation for reaction count updates
        pass
    
    async def start_polling(self):
        """Start the bot"""
        await self.initialize()
        logger.info("Starting test bot polling...")
        await self.dp.start_polling(self.bot)

async def main():
    """Main function"""
    bot = ArticleBotTest()
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
