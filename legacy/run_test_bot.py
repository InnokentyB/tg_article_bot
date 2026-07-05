#!/usr/bin/env python3
"""
Скрипт для запуска тестового бота
"""
import asyncio
import logging
from telegram_bot_test import ArticleBotTest

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Запуск тестового бота"""
    logger.info("🚀 Запуск тестового бота...")
    
    bot = ArticleBotTest()
    
    try:
        logger.info("📱 Тестовый бот запущен. Нажмите Ctrl+C для остановки.")
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("⚠️ Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
    finally:
        logger.info("🛑 Остановка тестового бота...")
        await bot.shutdown()
        logger.info("✅ Тестовый бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
