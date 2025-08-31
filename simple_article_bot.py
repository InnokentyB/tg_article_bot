#!/usr/bin/env python3
"""
Simple Telegram bot for article management demonstration
"""
import asyncio
import logging
import os
from typing import Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleArticleBot:
    def __init__(self):
        # Use a test token or get from environment
        self.token = os.getenv('ARTICLE_BOT_TOKEN', 'your_bot_token_here')
        if self.token == 'your_bot_token_here':
            logger.warning("⚠️ Using placeholder token. Please set ARTICLE_BOT_TOKEN in .env file")
            logger.info("📝 To get a bot token:")
            logger.info("1. Message @BotFather on Telegram")
            logger.info("2. Send /newbot")
            logger.info("3. Follow the instructions")
            logger.info("4. Copy the token to .env file")
            return
        
        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()
        
        # Register handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup message handlers"""
        self.dp.message(Command('start'))(self.cmd_start)
        self.dp.message(Command('help'))(self.cmd_help)
        self.dp.message(Command('stats'))(self.cmd_stats)
        self.dp.message()(self.process_message)
    
    async def cmd_start(self, message: Message):
        """Handle /start command"""
        user = message.from_user
        welcome_text = f"""
🤖 **Добро пожаловать в Article Management Bot!**

👋 Привет, {user.first_name}!

📰 Этот бот поможет вам:
• Сохранять и анализировать статьи
• Категоризировать контент
• Отслеживать источники
• Получать статистику

📋 **Доступные команды:**
/start - Начать работу
/help - Справка
/stats - Статистика

📝 **Как использовать:**
Просто отправьте ссылку на статью, и бот автоматически:
1. Извлечет текст
2. Определит категорию
3. Сохранит в базу данных
4. Покажет анализ

🚀 **Попробуйте отправить ссылку на любую статью!**
        """
        
        # Create inline keyboard
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="📊 Статистика", 
            callback_data="show_stats"
        ))
        builder.add(types.InlineKeyboardButton(
            text="❓ Помощь", 
            callback_data="show_help"
        ))
        builder.add(types.InlineKeyboardButton(
            text="🌐 Веб-админка", 
            url="https://tg-article-bot-api-production-12d6.up.railway.app"
        ))
        
        await message.answer(welcome_text, reply_markup=builder.as_markup())
    
    async def cmd_help(self, message: Message):
        """Handle /help command"""
        help_text = """
📚 **Справка по использованию бота**

🔗 **Отправка статей:**
Просто отправьте ссылку на статью в формате:
• https://example.com/article
• http://news.site.com/story
• www.blog.com/post

📊 **Команды:**
/start - Начать работу с ботом
/help - Показать эту справку
/stats - Показать статистику

🎯 **Функции:**
• Автоматическое извлечение текста
• Определение категории статьи
• Сохранение в базу данных
• Анализ контента
• Отслеживание источников

📱 **Веб-интерфейс:**
Для администраторов доступна веб-админка:
https://tg-article-bot-api-production-12d6.up.railway.app

🔧 **Поддержка:**
При возникновении проблем обратитесь к администратору.
        """
        await message.answer(help_text)
    
    async def cmd_stats(self, message: Message):
        """Handle /stats command"""
        stats_text = """
📊 **Статистика системы**

📰 **Статьи:**
• Всего статей: 0 (демо режим)
• За сегодня: 0
• За неделю: 0

👥 **Пользователи:**
• Всего пользователей: 1
• Активных сегодня: 1

📈 **Категории:**
• Технологии: 0
• Наука: 0
• Образование: 0
• Другие: 0

🔄 **Система:**
• Статус: Демо режим
• База данных: Не подключена
• API: Работает

💡 **Примечание:** Это демонстрационная версия бота.
        """
        
        # Create inline keyboard for stats
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="🔄 Обновить", 
            callback_data="refresh_stats"
        ))
        builder.add(types.InlineKeyboardButton(
            text="🌐 Веб-статистика", 
            url="https://tg-article-bot-api-production-12d6.up.railway.app/dashboard"
        ))
        
        await message.answer(stats_text, reply_markup=builder.as_markup())
    
    async def process_message(self, message: Message):
        """Process incoming messages"""
        text = message.text
        
        if not text:
            await message.answer("❌ Пожалуйста, отправьте текстовое сообщение или ссылку на статью.")
            return
        
        # Check if it's a URL
        if text.startswith(('http://', 'https://', 'www.')):
            await self.process_article_url(message, text)
        else:
            await self.process_text_message(message, text)
    
    async def process_article_url(self, message: Message, url: str):
        """Process article URL"""
        await message.answer("🔄 Обрабатываю статью...")
        
        # Simulate processing
        await asyncio.sleep(2)
        
        # Mock article processing with better categorization
        import random
        
        # Define categories and their keywords
        categories = {
            'Технологии': ['tech', 'programming', 'ai', 'machine', 'software', 'hardware', 'computer', 'digital', 'internet', 'web', 'app', 'mobile', 'cloud', 'data', 'algorithm'],
            'Наука': ['science', 'research', 'study', 'experiment', 'discovery', 'theory', 'physics', 'chemistry', 'biology', 'medicine', 'health', 'medical', 'clinical', 'laboratory'],
            'Бизнес': ['business', 'company', 'market', 'finance', 'economy', 'investment', 'startup', 'entrepreneur', 'management', 'strategy', 'profit', 'revenue', 'growth'],
            'Образование': ['education', 'learning', 'school', 'university', 'course', 'training', 'student', 'teacher', 'academic', 'knowledge', 'study', 'research'],
            'Медицина': ['health', 'medical', 'doctor', 'hospital', 'treatment', 'disease', 'patient', 'medicine', 'therapy', 'surgery', 'diagnosis', 'prevention'],
            'Финансы': ['finance', 'money', 'banking', 'investment', 'trading', 'stock', 'market', 'economy', 'currency', 'crypto', 'bitcoin', 'trading']
        }
        
        # Determine categories based on URL content
        url_lower = url.lower()
        detected_categories = []
        
        for category, keywords in categories.items():
            if any(keyword in url_lower for keyword in keywords):
                detected_categories.append(category)
        
        # If no categories detected, use default
        if not detected_categories:
            detected_categories = ['Технологии']
        
        # Primary category is the first one
        primary_category = detected_categories[0]
        
        # Generate random content length
        content_length = random.randint(800, 3000)
        
        article_info = {
            'title': f'Демонстрационная статья - {primary_category}',
            'category': primary_category,
            'categories': detected_categories,
            'content_length': content_length,
            'status': 'Обработана'
        }
        
        # Format categories for display
        if len(article_info['categories']) > 1:
            categories_text = f"🏷️ **Основная категория:** {article_info['category']}\n🏷️ **Все категории:** {', '.join(article_info['categories'])}"
        else:
            categories_text = f"🏷️ **Категория:** {article_info['category']}"
        
        result_text = f"""
✅ **Статья успешно обработана!**

📰 **Заголовок:** {article_info['title']}
{categories_text}
📏 **Длина текста:** {article_info['content_length']} символов
📊 **Статус:** {article_info['status']}

🔗 **Ссылка:** {url}

🎯 **Анализ:**
• Категория определена автоматически
• Контент проанализирован
• Дубликаты не найдены

💾 Статья сохранена в базу данных (демо режим).

📊 Хотите посмотреть статистику? Используйте /stats
        """
        
        # Create inline keyboard
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="📊 Статистика", 
            callback_data="show_stats"
        ))
        builder.add(types.InlineKeyboardButton(
            text="🌐 Веб-админка", 
            url="https://tg-article-bot-api-production-12d6.up.railway.app"
        ))
        
        await message.answer(result_text, reply_markup=builder.as_markup())
    
    async def process_text_message(self, message: Message, text: str):
        """Process text message"""
        response_text = f"""
💬 **Получено сообщение:**

{text}

📝 **Это текстовое сообщение, а не ссылка на статью.**

🔗 **Для обработки статьи отправьте ссылку в формате:**
• https://example.com/article
• http://news.site.com/story

📋 **Доступные команды:**
/start - Начать работу
/help - Справка
/stats - Статистика
        """
        await message.answer(response_text)
    
    async def run(self):
        """Run the bot"""
        if self.token == 'your_bot_token_here':
            logger.error("❌ Bot token not configured!")
            logger.info("📝 Please set ARTICLE_BOT_TOKEN in .env file")
            return
        
        try:
            logger.info("🚀 Starting Simple Article Bot...")
            logger.info("📱 Bot is now running. Press Ctrl+C to stop.")
            
            # Start polling
            await self.dp.start_polling(self.bot)
            
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Error running bot: {e}")
            raise
        finally:
            await self.bot.session.close()
            logger.info("✅ Bot shutdown completed")

async def main():
    """Main function"""
    bot = SimpleArticleBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
