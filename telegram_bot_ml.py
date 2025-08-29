#!/usr/bin/env python3
"""
Telegram Bot с интеграцией внешнего ML сервиса
"""
import asyncio
import logging
import os
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from database import DatabaseManager
from text_extractor import TextExtractor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArticleBotML:
    def __init__(self):
        self.token = os.getenv('ARTICLE_BOT_TOKEN')
        if not self.token:
            raise ValueError("ARTICLE_BOT_TOKEN environment variable is required")
        
        self.bot = Bot(token=self.token)
        storage = MemoryStorage()
        self.dp = Dispatcher(storage=storage)
        self.db = DatabaseManager()
        self.text_extractor = TextExtractor()
        
        # ML Service client
        self.ml_service_url = os.getenv('ML_SERVICE_URL', 'http://ml-service:8000')
        self.ml_client = httpx.AsyncClient(base_url=self.ml_service_url, timeout=30.0)
        
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
        logger.info("Bot initialized successfully with ML integration")
    
    async def shutdown(self):
        """Shutdown all components"""
        await self.db.close()
        await self.text_extractor.close()
        await self.ml_client.aclose()
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
🤖 Article Management Bot с ML

Отправьте мне:
• Текст статьи (минимум 50 символов)
• Ссылку на статью

Бот автоматически:
• Извлечет текст из ссылок
• Категоризует через ML
• Сохранит в базу данных

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
3. Бот автоматически:
   - Извлечет текст из ссылки
   - Категоризует через ML сервис
   - Сохранит в базу данных
   - Покажет результат

Функции:
• Автоматическое извлечение текста
• ML категоризация (OpenAI)
• Поиск дубликатов
• Статистика
        """
        await message.answer(help_text.strip())
    
    async def cmd_stats(self, message: Message):
        """Handle /stats command"""
        try:
            async with self.db.pool.acquire() as conn:
                articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
                users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            
            stats_text = f"""
📊 Статистика бота:

📰 Статей: {articles_count}
👥 Пользователей: {users_count}
🤖 ML сервис: активен
        """
            await message.answer(stats_text.strip())
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await message.answer("❌ Ошибка при получении статистики")
    
    async def process_message(self, message: Message):
        """Process incoming messages"""
        user = message.from_user
        if not user:
            return
        
        # Save user info
        await self.db.save_user(
            telegram_user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        text = message.text
        if not text:
            await message.answer("❌ Отправьте текст статьи или ссылку")
            return
        
        # Check if it's a URL
        original_url = None
        source_categories = []
        if text.startswith(('http://', 'https://')):
            original_url = text
            await message.answer("🔍 Извлекаю текст из ссылки...")
            try:
                extracted_data = await self.text_extractor.extract_from_url(text)
                if not extracted_data or not extracted_data.get('text') or len(extracted_data['text']) < 50:
                    await message.answer("❌ Не удалось извлечь текст из ссылки или текст слишком короткий")
                    return
                text = extracted_data['text']
                title = extracted_data.get('title') or "Без заголовка"
                source_categories = extracted_data.get('keywords', [])
            except Exception as e:
                logger.error(f"Error extracting text: {e}")
                await message.answer("❌ Ошибка при извлечении текста из ссылки")
                return
        
        # Check text length
        if len(text) < 50:
            await message.answer("❌ Текст должен содержать минимум 50 символов")
            return
        
        await message.answer("🤖 Обрабатываю статью через ML сервис...")
        
        try:
            # Get ML categorization
            ml_response = await self.ml_client.post("/categorize-detailed", json={
                "text": text[:1000],  # Limit for ML processing
                "title": None
            })
            
            if ml_response.status_code == 200:
                ml_result = ml_response.json()
                final_cat = ml_result.get('final_categorization', {})
                categories = final_cat.get('categories', ['General'])
                confidence = final_cat.get('confidence', 0.5)
                summary = final_cat.get('summary')
                ml_details = ml_result
            else:
                logger.warning(f"ML service error: {ml_response.text}")
                categories = ['General']
                confidence = 0.5
                summary = None
                ml_details = None
            
            # Save to database
            article_id, fingerprint = await self.db.save_article(
                title=title or "Без заголовка",  # Provide default title
                text=text,
                original_link=original_url,
                categories_user=categories,
                telegram_user_id=user.id
            )
            
            # Update automatic categories if we have them
            if article_id and source_categories:
                await self.db.update_article_categories(article_id, source_categories)
            
            if article_id:
                # Format response
                response_text = f"""
✅ Статья сохранена!

📝 ID: {article_id}
📄 Заголовок: {title or 'Без заголовка'}
🏷️ Категории: {', '.join(categories)}
🎯 Уверенность: {confidence:.1%}
🌐 Язык: {final_cat.get('language', 'не определен')}
🔍 Отпечаток: {fingerprint[:8]}...
📊 Слов: {len(text.split())}
🤖 Методы: {', '.join(ml_details.get('processing_methods', ['basic'])) if ml_details else 'basic'}
                """
                
                # Добавляем категории из источника
                if source_categories:
                    response_text += f"\n🏷️ Категории из источника: {', '.join(source_categories[:10])}"
                
                if summary:
                    response_text += f"\n📄 Краткое содержание:\n{summary}"
                
                # Добавляем детали по методам категоризации
                if ml_details:
                    basic_cat = ml_details.get('basic_categorization', {})
                    hf_cat = ml_details.get('huggingface_categorization')
                    openai_cat = ml_details.get('openai_categorization')
                    
                    response_text += f"\n\n🔍 Детали категоризации:"
                    response_text += f"\n📝 Базовый: {', '.join(basic_cat.get('categories', []))}"
                    
                    if hf_cat:
                        response_text += f"\n🤗 Hugging Face: {', '.join(hf_cat.get('categories', []))}"
                    
                    if openai_cat:
                        response_text += f"\n🧠 OpenAI: {', '.join(openai_cat.get('categories', []))}"
                
                await message.answer(response_text.strip())
            else:
                await message.answer("⚠️ Статья уже существует в базе данных")
                
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            await message.answer("❌ Ошибка при обработке статьи")

async def main():
    """Main function"""
    logger.info("Starting Telegram bot with ML integration...")
    
    bot = ArticleBotML()
    await bot.initialize()
    
    try:
        logger.info("Starting bot polling...")
        await bot.dp.start_polling(bot.bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
