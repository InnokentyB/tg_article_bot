"""
Test bot AI categorization with real API key
"""
import asyncio
from advanced_categorizer import AdvancedCategorizer

async def test_ai_categorization():
    print("Testing AI categorization with real OpenAI key...")
    
    categorizer = AdvancedCategorizer()
    
    if not categorizer.is_available():
        print("❌ Advanced categorizer not available")
        return
    
    print("✅ Advanced categorizer is available")
    
    try:
        # Test AI categorization
        result = await categorizer.categorize_article(
            text="Микросервисная архитектура с использованием Python и Docker позволяет создавать масштабируемые приложения. В статье рассматриваются паттерны проектирования, контейнеризация и оркестрация сервисов.",
            title="Микросервисы на Python: от монолита к распределенной системе"
        )
        
        print(f"✅ AI Categorization successful!")
        print(f"Primary category: {result['primary_category']} ({result['confidence']:.1%})")
        print(f"Subcategories: {result['subcategories']}")
        print(f"Keywords: {result['keywords']}")
        
    except Exception as e:
        print(f"❌ AI Categorization failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_categorization())