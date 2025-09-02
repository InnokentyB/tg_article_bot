#!/usr/bin/env python3
import asyncio
from text_extractor import TextExtractor

async def test_extractor():
    extractor = TextExtractor()
    try:
        await extractor.initialize()
        print("Extractor initialized")
        
        # Test with example.com
        result = await extractor.extract_from_url('https://example.com')
        print(f"Result for example.com: {result}")
        
        if result:
            print(f"Title: {result.get('title')}")
            print(f"Text length: {len(result.get('text', ''))}")
            print(f"Text preview: {result.get('text', '')[:200]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
    finally:
        await extractor.close()
        print("Extractor closed")

if __name__ == "__main__":
    asyncio.run(test_extractor())
