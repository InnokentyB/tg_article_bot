"""
Test improved text extraction quality
"""
import asyncio
from text_extractor import TextExtractor

async def test_extraction():
    print("Testing improved text extraction...")
    
    extractor = TextExtractor()
    await extractor.initialize()
    
    try:
        # Test with a Habr article
        result = await extractor.extract_from_url("https://habr.com/ru/articles/908850/")
        
        if result:
            print(f"✅ Title: {result['title'][:100]}...")
            print(f"✅ Text length: {len(result['text'])} characters")
            print(f"✅ First 200 chars: {result['text'][:200]}...")
            print(f"✅ Author: {result['author']}")
            print(f"✅ Source: {result['source']}")
            
            # Check quality metrics
            word_count = len(result['text'].split())
            print(f"✅ Word count: {word_count}")
            
            # Check for noise patterns
            noise_indicators = ['Поделиться', 'Комментарии', 'Реклама', 'Войти']
            noise_count = sum(1 for indicator in noise_indicators if indicator in result['text'])
            print(f"✅ Noise indicators found: {noise_count}/4")
            
        else:
            print("❌ Failed to extract content")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await extractor.close()

if __name__ == "__main__":
    asyncio.run(test_extraction())