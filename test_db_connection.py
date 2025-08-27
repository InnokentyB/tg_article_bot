#!/usr/bin/env python3
"""
Тест подключения к базе данных
"""
import asyncio
import asyncpg
import os

async def test_database_connection():
    """Тестирует подключение к PostgreSQL"""
    try:
        # Загружаем переменные окружения
        database_url = "postgresql://article_bot:article_bot_password@localhost:5432/article_bot"
        
        print("🔌 Подключение к базе данных...")
        conn = await asyncpg.connect(database_url)
        
        print("✅ Подключение успешно!")
        
        # Проверяем таблицы
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        print(f"📋 Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        # Проверяем количество записей
        articles_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        
        print(f"📊 Статистика:")
        print(f"   - Статей: {articles_count}")
        print(f"   - Пользователей: {users_count}")
        
        await conn.close()
        print("✅ Тест завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

async def test_redis_connection():
    """Тестирует подключение к Redis"""
    try:
        import redis.asyncio as redis
        
        print("\n🔌 Подключение к Redis...")
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Тестируем ping
        await r.ping()
        print("✅ Redis подключение успешно!")
        
        # Тестируем запись/чтение
        await r.set('test_key', 'test_value')
        value = await r.get('test_key')
        print(f"✅ Redis тест записи/чтения: {value}")
        
        await r.close()
        
    except Exception as e:
        print(f"❌ Ошибка Redis: {e}")

async def main():
    """Основная функция"""
    print("🧪 Тестирование подключений к сервисам...\n")
    
    await test_database_connection()
    await test_redis_connection()
    
    print("\n🎉 Все тесты завершены!")

if __name__ == "__main__":
    asyncio.run(main())
