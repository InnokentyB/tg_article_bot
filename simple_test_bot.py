#!/usr/bin/env python3
"""
Упрощенный тестовый бот для диагностики
"""
import asyncio
import logging
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

class SimpleTestBot:
    def __init__(self):
        # Используем тестовый токен
        self.token = os.getenv('ARTICLE_BOT_TEST_TOKEN', '8270061551:AAFC5sxwxTM4zz8mzy7quKbSvG85lkGbyDs')
        logger.info(f"Используем токен: {self.token[:10]}...{self.token[-10:]}")
        
        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()
        
        # Регистрируем обработчики
        self.dp.message(Command('start'))(self.cmd_start)
        self.dp.message(Command('help'))(self.cmd_help)
        self.dp.message()(self.process_message)
    
    async def cmd_start(self, message: types.Message):
        """Обработка команды /start"""
        logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
        
        welcome_text = f"""
🤖 **Тестовый бот - УПРОЩЕННАЯ ВЕРСИЯ**

👋 Привет, {message.from_user.first_name}!

🔬 **Это тестовое окружение**
• Упрощенная версия бота
• Только базовые функции
• Для диагностики проблем

📝 **Как использовать:**
1. Отправьте ссылку на статью
2. Получите простой ответ
3. Проверьте работу бота

🔧 **Доступные команды:**
/start - Начать работу
/help - Справка

🚀 **Отправьте ссылку на статью для тестирования!**
        """
        
        await message.answer(welcome_text)
        logger.info("Отправлено приветственное сообщение")
    
    async def cmd_help(self, message: types.Message):
        """Обработка команды /help"""
        help_text = """
📚 **Справка по тестовому боту**

🔬 **Это упрощенная версия для диагностики:**
• Базовая обработка сообщений
• Простое извлечение URL
• Минимальная функциональность

📝 **Что работает:**
• Команды /start и /help
• Обработка ссылок
• Простые ответы

❓ **Для полного функционала используйте основной бот**
        """
        await message.answer(help_text)
    
    async def process_message(self, message: types.Message):
        """Обработка обычных сообщений"""
        if not message.text:
            await message.answer("Пожалуйста, отправьте текстовое сообщение")
            return
        
        text = message.text.strip()
        logger.info(f"Получено сообщение: {text[:50]}...")
        
        # Проверяем, является ли это URL
        if text.startswith(('http://', 'https://')):
            await self.process_url(message, text)
        else:
            await message.answer(
                "🔗 Пожалуйста, отправьте ссылку на статью для обработки.\n\n"
                "Или используйте команды:\n"
                "/start - Начать работу\n"
                "/help - Справка"
            )
    
    async def process_url(self, message: types.Message, url: str):
        """Обработка URL"""
        logger.info(f"Обрабатываем URL: {url}")
        
        # Отправляем статус
        status_msg = await message.answer("🔄 Обрабатываю ссылку...")
        
        try:
            # Имитируем обработку
            await asyncio.sleep(2)
            
            # Простой ответ
            response_text = f"""
✅ **Ссылка обработана - ТЕСТОВАЯ ВЕРСИЯ**

🔗 **URL:** {url}

🔬 **Тестовые данные:**
• Статус: Обработано
• Тип: Веб-страница
• Версия: Упрощенная

📝 **Это тестовое окружение:**
• Минимальная обработка
• Для диагностики
• Без реальной категоризации

🎯 **Тест успешен!**
            """
            
            await status_msg.edit_text(response_text)
            logger.info("URL успешно обработан")
            
        except Exception as e:
            logger.error(f"Ошибка обработки URL: {e}")
            await status_msg.edit_text(f"❌ Ошибка при обработке: {str(e)}")
    
    async def start(self):
        """Запуск бота"""
        logger.info("🚀 Запуск упрощенного тестового бота...")
        
        try:
            # Удаляем webhook
            await self.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook удален")
            
            # Запускаем polling
            logger.info("📱 Бот запущен. Нажмите Ctrl+C для остановки.")
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
        finally:
            await self.bot.session.close()
            logger.info("✅ Бот остановлен")

async def main():
    """Основная функция"""
    bot = SimpleTestBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
