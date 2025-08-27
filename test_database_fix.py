"""
Test database JSON serialization fix
"""
import asyncio
import json
from database import DatabaseManager

async def test_db_fix():
    print("Testing database JSON serialization fix...")
    
    db = DatabaseManager()
    await db.initialize()
    
    try:
        # Test categories_advanced as dict
        advanced_categories = {
            "id": "test-123",
            "title": "Test Article",
            "primary_category": "Technology",
            "primary_category_label": "Технологии",
            "subcategories": ["AI", "Machine Learning"],
            "keywords": ["python", "database", "json"],
            "confidence": 0.85,
            "summary": "Test summary"
        }
        
        article_id, fingerprint = await db.save_article(
            title="Test JSON Article",
            text="This is a test article for JSON serialization",
            summary="Test summary",
            categories_advanced=advanced_categories,
            language="en",
            telegram_user_id=123456
        )
        
        if article_id:
            print(f"✅ Article saved successfully with ID: {article_id}")
            
            # Retrieve and verify
            saved_article = await db.get_article_by_id(article_id)
            if saved_article:
                print(f"✅ Article retrieved successfully")
                print(f"Advanced categories type: {type(saved_article.get('categories_advanced'))}")
                if saved_article.get('categories_advanced'):
                    print(f"Advanced categories content: {saved_article['categories_advanced']}")
                else:
                    print("⚠️  No advanced categories found")
            else:
                print("❌ Failed to retrieve saved article")
        else:
            print("❌ Failed to save article (duplicate?)")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        await db.close()
    
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_db_fix())