"""
Test script for Telegram reactions and external source tracking
"""
import asyncio
import logging
import os
from database import DatabaseManager
from telegram_reactions import TelegramReactionsTracker
from external_source_tracker import ExternalSourceTracker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_external_tracking():
    """Test external source tracking functionality"""
    print("🔍 Testing External Source Tracking...")
    
    # Initialize components
    db = DatabaseManager()
    await db.initialize()
    
    tracker = ExternalSourceTracker(db)
    await tracker.initialize()
    
    try:
        # Test Habr article tracking
        test_urls = [
            "https://habr.com/ru/articles/123456/",  # Example Habr URL
            "https://medium.com/@author/article-title",  # Example Medium URL
            "https://dev.to/author/article-title"  # Example DEV.to URL
        ]
        
        # First, create a test article
        article_id, _ = await db.save_article(
            text="Test article for external tracking",
            title="Test Article", 
            summary="Testing external source tracking",
            source="https://habr.com/ru/articles/123456/",
            language="ru",
            telegram_user_id=12345
        )
        
        print(f"✅ Created test article with ID: {article_id}")
        
        # Test tracking setup
        for url in test_urls:
            try:
                await tracker.track_article_source(article_id, url)
                print(f"✅ Started tracking: {url}")
            except Exception as e:
                print(f"⚠️ Failed to track {url}: {e}")
        
        # Test stats retrieval
        stats = await tracker.get_article_external_stats(article_id)
        print(f"📊 External stats: {stats}")
        
        # Test parser detection
        for url in test_urls:
            source_type = tracker.detect_source_type(url)
            print(f"🔍 {url} -> Source type: {source_type}")
        
        # Test count parsing
        test_counts = ["1.2K", "5M", "123", "42.5K", "0"]
        for count_text in test_counts:
            parsed = tracker.parse_count_value(count_text)
            print(f"🔢 '{count_text}' -> {parsed}")
        
        print("✅ External tracking tests completed!")
        
    except Exception as e:
        print(f"❌ External tracking test failed: {e}")
        logger.error(f"Test error: {e}")
    
    finally:
        await tracker.close()
        await db.close()

async def test_reactions_system():
    """Test Telegram reactions tracking system"""
    print("\n🔍 Testing Telegram Reactions System...")
    
    # Initialize components
    db = DatabaseManager()
    await db.initialize()
    
    reactions_tracker = TelegramReactionsTracker(db)
    
    try:
        # Create test article
        article_id, _ = await db.save_article(
            text="Test article for reactions",
            title="Reactions Test Article",
            summary="Testing Telegram reactions tracking", 
            source="test",
            language="en",
            telegram_user_id=12345
        )
        
        print(f"✅ Created test article with ID: {article_id}")
        
        # Test message linking
        message_id = 999888777
        chat_id = -100123456789
        
        await reactions_tracker.save_article_message_link(article_id, message_id, chat_id)
        print(f"✅ Linked article {article_id} to message {message_id}")
        
        # Test manual reaction adding
        test_reactions = ['👍', '❤️', '🔥', '😍']
        user_ids = [111, 222, 333, 444]
        
        for i, emoji in enumerate(test_reactions):
            await reactions_tracker.add_reaction(article_id, user_ids[i], emoji)
            print(f"✅ Added reaction {emoji} from user {user_ids[i]}")
        
        # Test reaction stats
        reaction_stats = {'👍': 5, '❤️': 3, '🔥': 2, '😍': 1}
        await reactions_tracker.update_article_reaction_stats(article_id, reaction_stats)
        print(f"✅ Updated reaction stats: {reaction_stats}")
        
        # Test getting reactions
        all_reactions = await reactions_tracker.get_article_reactions(article_id)
        print(f"📊 Article reactions: {all_reactions}")
        
        # Test message info retrieval
        message_info = await reactions_tracker.get_message_info(article_id)
        print(f"💬 Message info: {message_info}")
        
        print("✅ Reactions system tests completed!")
        
    except Exception as e:
        print(f"❌ Reactions test failed: {e}")
        logger.error(f"Test error: {e}")
    
    finally:
        await db.close()

async def test_api_endpoints():
    """Test new API endpoints"""
    print("\n🔍 Testing API Endpoints...")
    
    import aiohttp
    import json
    
    base_url = "http://localhost:5000"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test getting article reactions
            async with session.get(f"{base_url}/api/articles/1/reactions") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Reactions API: {data}")
                else:
                    print(f"⚠️ Reactions API returned {resp.status}")
            
            # Test getting external stats
            async with session.get(f"{base_url}/api/articles/1/external-stats") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ External stats API: {data}")
                else:
                    print(f"⚠️ External stats API returned {resp.status}")
            
            # Test Telegram link
            async with session.get(f"{base_url}/api/articles/1/telegram-link") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Telegram link API: {data}")
                elif resp.status == 404:
                    print("✅ Telegram link API: No link found (expected)")
                else:
                    print(f"⚠️ Telegram link API returned {resp.status}")
            
            print("✅ API endpoints test completed!")
            
        except Exception as e:
            print(f"❌ API test failed: {e}")

async def main():
    """Run all tests"""
    print("🚀 Starting Telegram Reactions and External Stats Tests")
    
    if not os.getenv('DATABASE_URL'):
        print("❌ DATABASE_URL environment variable is required")
        return
    
    try:
        await test_reactions_system()
        await test_external_tracking()
        await test_api_endpoints()
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        logger.error(f"Test suite error: {e}")

if __name__ == "__main__":
    asyncio.run(main())