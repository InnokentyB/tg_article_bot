"""
Telegram bot for article management
"""
import asyncio
import logging
import os
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, MessageReactionUpdated, MessageReactionCountUpdated
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from database import DatabaseManager
from text_extractor import TextExtractor
from article_categorizer import ArticleCategorizer
from advanced_categorizer import AdvancedCategorizer
from telegram_reactions import TelegramReactionsTracker
from external_source_tracker import ExternalSourceTracker

logger = logging.getLogger(__name__)

class ArticleStates(StatesGroup):
    waiting_for_categories = State()

class ArticleBot:
    def __init__(self):
        self.token = os.getenv('ARTICLE_BOT_TOKEN')
        if not self.token:
            raise ValueError("ARTICLE_BOT_TOKEN environment variable is required")
        
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
        logger.info("Bot initialized successfully")
    
    async def shutdown(self):
        """Shutdown all components"""
        await self.db.close()
        await self.text_extractor.close()
        await self.external_tracker.close()
        await self.bot.session.close()
        logger.info("Bot shutdown completed")
    
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
🤖 *Добро пожаловать в бот для сохранения статей!*

Я помогу вам сохранять и каталогизировать статьи. Просто отправьте мне:

📝 *Текст статьи* - прямо в сообщении
🔗 *Ссылку на статью* - я извлеку текст автоматически

Функции:
• Автоматическая проверка дубликатов
• Категоризация статей
• Определение языка
• Поиск и фильтрация

Команды:
/help - показать справку
/stats - показать статистику
        """
        
        await message.answer(welcome_text, parse_mode="Markdown")
    
    async def cmd_help(self, message: Message):
        """Handle /help command"""
        help_text = """
📚 *Справка по использованию бота*

*Как добавить статью:*
1. Отправьте текст статьи в сообщении
2. Или отправьте ссылку на статью - я извлеку текст

*Что происходит при добавлении:*
• Проверяется на дубликаты (по fingerprint)
• Определяется язык статьи
• Выполняется автоматическая категоризация
• Сохраняется в базу данных

*Если найден дубликат:*
• Я покажу информацию о найденной статье
• Данные о просмотрах, лайках и комментариях
• Дату добавления и категории

*Команды:*
/start - начать работу
/help - эта справка  
/stats - ваша статистика

*API для разработчиков:*
• GET /api/articles - список статей
• GET /api/articles/{id} - статья по ID
• PUT /api/articles/{id}/counters - обновить счетчики
        """
        
        await message.answer(help_text, parse_mode="Markdown")
    
    async def cmd_stats(self, message: Message):
        """Handle /stats command"""
        if not message.from_user:
            await message.answer("❌ Не удалось определить пользователя")
            return
        user_id = message.from_user.id
        
        # Get user's articles
        articles = await self.db.get_articles(user_id=user_id, limit=1000)
        
        if not articles:
            await message.answer("📊 У вас пока нет сохраненных статей")
            return
        
        # Calculate stats
        total_articles = len(articles)
        categories = {}
        languages = {}
        
        for article in articles:
            # Count categories
            for cat in (article.get('categories_auto') or []):
                categories[cat] = categories.get(cat, 0) + 1
            
            # Count languages
            lang = article.get('language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
        
        # Format stats
        stats_text = f"📊 *Ваша статистика*\n\n"
        stats_text += f"📝 Всего статей: *{total_articles}*\n\n"
        
        if categories:
            stats_text += "📂 *По категориям:*\n"
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                stats_text += f"• {cat}: {count}\n"
            stats_text += "\n"
        
        if languages:
            stats_text += "🌐 *По языкам:*\n"
            for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                lang_name = {'ru': 'Русский', 'en': 'English', 'unknown': 'Неизвестный'}.get(lang, lang)
                stats_text += f"• {lang_name}: {count}\n"
        
        await message.answer(stats_text, parse_mode="Markdown")
    
    async def cmd_cancel(self, message: Message, state: FSMContext):
        """Handle /cancel command"""
        await state.clear()
        await message.answer("❌ Действие отменено")
    
    async def process_message(self, message: Message, state: FSMContext):
        """Process incoming messages (text or URLs) - only when NOT in FSM state"""
        current_state = await state.get_state()
        if current_state:
            # If user is in FSM state, this shouldn't be called
            logger.warning(f"process_message called while in state {current_state}")
            return
            
        if not message.text:
            await message.answer("❌ Пожалуйста, отправьте текст статьи или ссылку")
            return
        
        text = message.text.strip()
        user_id = message.from_user.id if message.from_user else 0
        logger.info(f"Processing new message from user {user_id}: {text[:50]}...")
        
        # Check if it's a URL
        if self.text_extractor.is_valid_url(text):
            await self.process_url(message, text)
        else:
            await self.process_text(message, text)
    
    async def process_url(self, message: Message, url: str):
        """Process URL message"""
        status_msg = await message.answer("🔄 Извлекаю текст из ссылки...")
        
        try:
            # Extract content from URL
            content = await self.text_extractor.extract_from_url(url)
            
            if not content or not content['text']:
                await status_msg.edit_text("❌ Не удалось извлечь текст из ссылки")
                return
            
            # Check for duplicates
            fingerprint = self.db.generate_fingerprint(content['text'])
            duplicate = await self.db.check_duplicate(fingerprint)
            
            if duplicate:
                await self.show_duplicate(status_msg, duplicate)
                return
            
            # Detect language and basic categorize
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
            success_text = f"✅ *Статья сохранена!*\n\n"
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
                success_text += f"🏷️ *Категории:* {', '.join(categories)}\n"
            
            success_text += f"🌐 *Язык:* {language}\n"
            success_text += f"📊 *ID:* {article_id}\n"
            
            if content['author']:
                success_text += f"✍️ *Автор:* {content['author']}\n"
            
            await status_msg.edit_text(success_text, parse_mode="Markdown")
            
            # Link article to message and start external tracking
            if article_id is not None:
                await self.reactions_tracker.save_article_message_link(
                    article_id, status_msg.message_id, message.chat.id
                )
                
                # Start tracking external source
                if content.get('source'):
                    await self.external_tracker.track_article_source(article_id, content['source'])
                
                # Ask for user categories with stats
                await self.ask_for_categories_with_stats(message, article_id)
            
        except Exception as e:
            logger.error(f"Error processing URL: {e}")
            await status_msg.edit_text("❌ Произошла ошибка при обработке ссылки")
    
    async def process_text(self, message: Message, text: str):
        """Process text message"""
        if len(text) < 50:
            await message.answer("❌ Текст слишком короткий для сохранения (минимум 50 символов)")
            return
        
        status_msg = await message.answer("🔄 Обрабатываю статью...")
        
        try:
            # Check for duplicates
            fingerprint = self.db.generate_fingerprint(text)
            duplicate = await self.db.check_duplicate(fingerprint)
            
            if duplicate:
                await self.show_duplicate(status_msg, duplicate)
                return
            
            # Detect language and basic categorize
            language = self.categorizer.detect_language(text)
            categories = self.categorizer.categorize_article(text)
            
            # Advanced categorization with OpenAI (if available)
            advanced_categories = None
            try:
                if self.advanced_categorizer.is_available():
                    await status_msg.edit_text("🤖 Выполняю углубленную категоризацию...")
                    advanced_categories = await self.advanced_categorizer.categorize_article(
                        text, "", language
                    )
                    logger.info(f"Advanced categorization completed: {advanced_categories['primary_category']}")
            except Exception as e:
                logger.error(f"Advanced categorization failed: {e}")
            
            # Generate summary (use AI summary if available)
            summary = advanced_categories.get('summary') if advanced_categories else None
            if not summary:
                summary = self.text_extractor.generate_summary(text)
            
            # Save article
            user_id = message.from_user.id if message.from_user else None
            article_id, _ = await self.db.save_article(
                text=text,
                summary=summary,
                categories_advanced=advanced_categories,
                language=language,
                telegram_user_id=user_id
            )
            
            # Update categories
            await self.db.update_article_categories(article_id, categories)
            
            # Success message with dual categorization info
            success_text = f"✅ *Статья сохранена!*\n\n"
            
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
                success_text += f"🏷️ *Категории:* {', '.join(categories)}\n"
            
            success_text += f"🌐 *Язык:* {language}\n"
            success_text += f"📊 *ID:* {article_id}\n"
            
            await status_msg.edit_text(success_text, parse_mode="Markdown")
            
            # Link article to message for reactions tracking
            if article_id is not None:
                await self.reactions_tracker.save_article_message_link(
                    article_id, status_msg.message_id, message.chat.id
                )
                
                # Ask for user categories with stats
                await self.ask_for_categories_with_stats(message, article_id)
            
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            await status_msg.edit_text("❌ Произошла ошибка при обработке текста")
    
    async def show_duplicate(self, message: Message, duplicate: dict):
        """Show duplicate article information"""
        duplicate_text = f"🔄 *Дубликат найден!*\n\n"
        
        if duplicate['title']:
            duplicate_text += f"📰 *Заголовок:* {duplicate['title']}\n"
        
        duplicate_text += f"📅 *Дата добавления:* {duplicate['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
        
        if duplicate['categories_auto']:
            duplicate_text += f"🏷️ *Категории:* {', '.join(duplicate['categories_auto'])}\n"
        
        if duplicate['categories_user']:
            duplicate_text += f"👤 *Пользовательские категории:* {', '.join(duplicate['categories_user'])}\n"
        
        if duplicate['source']:
            duplicate_text += f"🌐 *Источник:* {duplicate['source']}\n"
        
        if duplicate['author']:
            duplicate_text += f"✍️ *Автор:* {duplicate['author']}\n"
        
        duplicate_text += f"📊 *ID:* {duplicate['id']}\n"
        
        await message.edit_text(duplicate_text, parse_mode="Markdown")
    
    async def ask_for_categories(self, message: Message, article_id: int):
        """Ask user for additional categories"""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(types.InlineKeyboardButton(
            text="➕ Добавить категории",
            callback_data=f"add_categories:{article_id}"
        ))
        keyboard.add(types.InlineKeyboardButton(
            text="✅ Готово",
            callback_data=f"done:{article_id}"
        ))
        
        await message.answer(
            "Хотите добавить свои категории к статье?",
            reply_markup=keyboard.as_markup()
        )
    
    async def ask_for_categories_with_stats(self, message: Message, article_id: int):
        """Ask user for categories with additional options for stats and external tracking"""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(types.InlineKeyboardButton(
            text="➕ Добавить категории",
            callback_data=f"add_categories:{article_id}"
        ))
        keyboard.add(types.InlineKeyboardButton(
            text="📊 Показать статистику",
            callback_data=f"stats:{article_id}"
        ))
        keyboard.add(types.InlineKeyboardButton(
            text="🔗 Отслеживать источник",
            callback_data=f"track_external:{article_id}"
        ))
        keyboard.add(types.InlineKeyboardButton(
            text="✅ Готово",
            callback_data=f"done:{article_id}"
        ))
        
        await message.answer(
            "Хотите добавить категории или настроить отслеживание статистики?",
            reply_markup=keyboard.as_markup()
        )
    
    async def callback_add_categories(self, callback: CallbackQuery, state: FSMContext):
        """Handle add categories callback"""
        data = callback.data
        if not data:
            await callback.answer("❌ Неверные данные")
            return
            
        article_id = int(data.split(":")[1])
        
        # Save article_id to state
        await state.update_data(article_id=article_id)
        await state.set_state(ArticleStates.waiting_for_categories)
        
        if callback.message and hasattr(callback.message, 'edit_text'):
            await callback.message.edit_text(
                f"📝 Отправьте категории для статьи {article_id} через запятую:\n"
                "Например: технологии, программирование, AI\n\n"
                "Или отправьте /cancel для отмены"
            )
        
        await callback.answer("Жду ваши категории...")
    
    async def callback_done(self, callback: CallbackQuery):
        """Handle done callback"""
        if callback.message and hasattr(callback.message, 'edit_text'):
            await callback.message.edit_text("✅ Статья успешно сохранена!")
        await callback.answer()
    
    async def process_categories(self, message: Message, state: FSMContext):
        """Process user categories input - this handler is called when user is in waiting_for_categories state"""
        user_id = message.from_user.id if message.from_user else 0
        logger.info(f"Processing categories from user {user_id}: {message.text}")
        
        if message.text and message.text.startswith('/cancel'):
            await state.clear()
            await message.answer("❌ Добавление категорий отменено")
            return
            
        if not message.text:
            await message.answer("❌ Пожалуйста, отправьте категории текстом")
            return
            
        # Get article_id from state
        data = await state.get_data()
        article_id = data.get('article_id')
        
        if not article_id:
            await message.answer("❌ Ошибка: не найден ID статьи")
            await state.clear()
            return
            
        # Parse categories
        categories_text = message.text.strip()
        user_categories = [cat.strip() for cat in categories_text.split(',') if cat.strip()]
        
        if not user_categories:
            await message.answer("❌ Не удалось распознать категории. Попробуйте еще раз")
            return
            
        try:
            # Get current article to update user categories
            article = await self.db.get_article_by_id(article_id)
            if not article:
                await message.answer("❌ Статья не найдена")
                await state.clear()
                return
                
            # Update user categories in database
            if not self.db.pool:
                raise RuntimeError("Database pool not initialized")
            async with self.db.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE articles SET categories_user = $2, updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                    article_id, user_categories
                )
            
            await message.answer(
                f"✅ Добавлены пользовательские категории:\n"
                f"🏷️ {', '.join(user_categories)}\n\n"
                f"Статья {article_id} обновлена!"
            )
            
        except Exception as e:
            logger.error(f"Error updating user categories: {e}")
            await message.answer("❌ Произошла ошибка при сохранении категорий")
            
        await state.clear()
    
    async def handle_message_reaction(self, reaction: MessageReactionUpdated):
        """Handle message reactions for tracking article engagement"""
        try:
            await self.reactions_tracker.handle_message_reaction(reaction)
        except Exception as e:
            logger.error(f"Error handling message reaction: {e}")
    
    async def handle_message_reaction_count(self, reaction_count: MessageReactionCountUpdated):
        """Handle message reaction counts for tracking article engagement"""
        try:
            await self.reactions_tracker.handle_message_reaction_count(reaction_count)
        except Exception as e:
            logger.error(f"Error handling message reaction count: {e}")
    
    async def callback_show_stats(self, callback: CallbackQuery):
        """Show article statistics including reactions and external stats"""
        try:
            data = callback.data
            if not data:
                await callback.answer("❌ Неверные данные")
                return
                
            article_id = int(data.split(":")[1])
            
            # Get Telegram reactions
            telegram_stats = await self.reactions_tracker.get_article_reactions(article_id)
            
            # Get external source stats
            external_stats = await self.external_tracker.get_article_external_stats(article_id)
            
            # Format stats message
            stats_text = f"📊 *Статистика статьи {article_id}*\n\n"
            
            # Telegram stats
            if telegram_stats['reaction_counts']:
                stats_text += "🤖 *Telegram реакции:*\n"
                for emoji, count in telegram_stats['reaction_counts'].items():
                    stats_text += f"  {emoji} {count}\n"
                stats_text += f"📊 Всего лайков: {telegram_stats['total_likes']}\n"
                stats_text += f"👀 Просмотров: {telegram_stats['total_views']}\n\n"
            
            # External stats
            if external_stats:
                for source_type, stats in external_stats.items():
                    stats_text += f"🌐 *{source_type.title()}:*\n"
                    stats_text += f"  👀 Просмотры: {stats['views']}\n"
                    stats_text += f"  💬 Комментарии: {stats['comments']}\n"
                    stats_text += f"  👍 Лайки: {stats['likes']}\n"
                    if stats['bookmarks'] > 0:
                        stats_text += f"  🔖 Закладки: {stats['bookmarks']}\n"
                    stats_text += f"  🕐 Обновлено: {stats['last_updated'].strftime('%d.%m %H:%M')}\n\n"
            
            if not telegram_stats['reaction_counts'] and not external_stats:
                stats_text += "📊 Статистика пока недоступна\n"
                stats_text += "Добавьте реакции к сообщению или настройте отслеживание источника"
            
            if callback.message and hasattr(callback.message, 'edit_text'):
                await callback.message.edit_text(stats_text, parse_mode="Markdown")
            
            await callback.answer("Статистика обновлена!")
            
        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            await callback.answer("❌ Ошибка при загрузке статистики")
    
    async def callback_track_external(self, callback: CallbackQuery):
        """Handle external source tracking setup"""
        try:
            data = callback.data
            if not data:
                await callback.answer("❌ Неверные данные")
                return
                
            article_id = int(data.split(":")[1])
            
            if callback.message and hasattr(callback.message, 'edit_text'):
                await callback.message.edit_text(
                    f"🔗 Отправьте ссылку на источник статьи {article_id} для отслеживания статистики:\n\n"
                    "Поддерживаются:\n"
                    "• Habr.com\n"
                    "• Medium.com\n"
                    "• DEV.to\n\n"
                    "Или отправьте /cancel для отмены"
                )
            
            await callback.answer("Жду ссылку на источник...")
            
        except Exception as e:
            logger.error(f"Error in track external callback: {e}")
            await callback.answer("❌ Ошибка настройки отслеживания")
    
    async def start_polling(self):
        """Start bot polling"""
        await self.initialize()
        logger.info("Starting bot polling...")
        try:
            # Configure allowed updates to include reactions
            allowed_updates = ['message', 'callback_query', 'message_reaction', 'message_reaction_count']
            await self.dp.start_polling(self.bot, allowed_updates=allowed_updates)
        finally:
            await self.shutdown()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = ArticleBot()
    asyncio.run(bot.start_polling())
