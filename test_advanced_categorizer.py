"""
Test script for advanced categorizer integration
"""
import asyncio
import logging
import os
from database import DatabaseManager
from advanced_categorizer import AdvancedCategorizer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_advanced_categorizer():
    """Test the advanced categorizer system"""
    print("🧠 Testing Advanced Article Categorizer")
    
    # Initialize components
    db = DatabaseManager()
    await db.initialize()
    
    categorizer = AdvancedCategorizer()
    
    try:
        if not categorizer.is_available():
            print("⚠️  OpenAI API key not available - advanced categorizer disabled")
            print("💡 To enable: Set OPENAI_API_KEY environment variable")
            return
        
        print("✅ OpenAI API key found - testing categorization...")
        
        # Test article for categorization
        test_text = """
        Искусственный интеллект революционизирует финтех индустрию. Машинное обучение 
        позволяет банкам автоматизировать процессы кредитного скоринга и выявления 
        мошенничества. Новые алгоритмы глубокого обучения обрабатывают транзакции 
        в режиме реального времени, обеспечивая безопасность платежей.
        """
        
        test_title = "ИИ в финансовых технологиях: революция банковского дела"
        
        # Perform advanced categorization
        result = await categorizer.categorize_article(test_text, test_title, "ru")
        
        print(f"📊 Categorization Result:")
        print(f"🎯 Primary Category: {result['primary_category_label']}")
        print(f"📂 Subcategories: {', '.join(result['subcategories'])}")
        print(f"🏷️  Keywords: {', '.join(result['keywords'])}")
        print(f"🎲 Confidence: {result['confidence']:.1%}")
        print(f"📝 Summary: {result['summary'][:200]}...")
        
        # Test saving to database with advanced categories
        article_id, fingerprint = await db.save_article(
            text=test_text,
            title=test_title,
            summary=result['summary'],
            categories_advanced=result,
            language="ru",
            telegram_user_id=999999
        )
        
        if article_id:
            print(f"✅ Article saved to database with ID: {article_id}")
            
            # Retrieve and verify
            saved_article = await db.get_article_by_id(article_id)
            if saved_article and saved_article.get('categories_advanced'):
                print("✅ Advanced categories saved and retrieved successfully")
                print(f"💾 Saved categories: {saved_article['categories_advanced']['primary_category']}")
            else:
                print("⚠️  Advanced categories not saved properly")
        else:
            print("❌ Failed to save article (duplicate?)")
        
        print("🎉 Advanced categorizer test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Test error: {e}")
    
    finally:
        await db.close()

async def test_basic_vs_advanced():
    """Compare basic vs advanced categorization"""
    print("\n🔬 Comparing Basic vs Advanced Categorization")
    
    # Initialize
    db = DatabaseManager()
    await db.initialize()
    
    from article_categorizer import ArticleCategorizer
    basic_categorizer = ArticleCategorizer()
    advanced_categorizer = AdvancedCategorizer()
    
    test_text = """
    Разработка микросервисной архитектуры для высоконагруженных систем требует 
    глубокого понимания паттернов проектирования. Использование Docker и Kubernetes 
    позволяет обеспечить масштабируемость и отказоустойчивость приложений. 
    Система мониторинга и логирования играет ключевую роль в DevOps процессах.
    """
    
    try:
        # Basic categorization
        basic_categories = basic_categorizer.categorize_article(test_text)
        print(f"🔧 Basic Categories: {', '.join(basic_categories)}")
        
        # Advanced categorization (if available)
        if advanced_categorizer.is_available():
            advanced_result = await advanced_categorizer.categorize_article(test_text)
            print(f"🧠 Advanced Category: {advanced_result['primary_category_label']}")
            print(f"📂 Subcategories: {', '.join(advanced_result['subcategories'])}")
            print(f"🏷️  Keywords: {', '.join(advanced_result['keywords'][:5])}")
            print(f"🎲 Confidence: {advanced_result['confidence']:.1%}")
        else:
            print("⚠️  Advanced categorizer not available")
    
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
    
    finally:
        await db.close()

async def main():
    """Run all tests"""
    print("🚀 Starting Advanced Categorizer Integration Tests")
    
    await test_advanced_categorizer()
    await test_basic_vs_advanced()
    
    print("\n✨ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())