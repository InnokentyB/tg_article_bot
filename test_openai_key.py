"""
Test OpenAI API key status
"""
import os
from openai import OpenAI

def test_openai_key():
    print("Testing OpenAI API key...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OPENAI_API_KEY found in environment")
        return
    
    print(f"🔑 Key found: {api_key[:20]}...")
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'OK' if this works"}],
            max_tokens=5
        )
        
        print(f"✅ API Response: {response.choices[0].message.content}")
        print("✅ OpenAI API key is working correctly!")
        
    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    test_openai_key()