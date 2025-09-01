#!/usr/bin/env python3
"""
Test bot configuration without starting the bot
"""
import os
import sys
import asyncio

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config():
    """Test bot configuration"""
    print("🧪 Testing bot configuration...")
    
    # Test environment variables
    print("\n📋 Environment variables:")
    print(f"ARTICLE_BOT_TOKEN: {'✅ Set' if os.getenv('ARTICLE_BOT_TOKEN') else '❌ Not set'}")
    print(f"RAILWAY_API_URL: {'✅ Set' if os.getenv('RAILWAY_API_URL') else '❌ Not set'}")
    print(f"USE_RAILWAY_API: {'✅ Set' if os.getenv('USE_RAILWAY_API') else '❌ Not set'}")
    
    # Test imports
    print("\n📦 Testing imports:")
    try:
        from config_railway import RailwayConfig
        print("✅ RailwayConfig imported successfully")
        
        config = RailwayConfig()
        print(f"✅ Configuration created: {config.get_railway_info()}")
        
    except ImportError as e:
        print(f"❌ Failed to import RailwayConfig: {e}")
        return False
    
    try:
        from railway_api_client import RailwayAPIClient
        print("✅ RailwayAPIClient imported successfully")
        
    except ImportError as e:
        print(f"❌ Failed to import RailwayAPIClient: {e}")
        return False
    
    try:
        from telegram_bot_railway import RailwayArticleBot
        print("✅ RailwayArticleBot imported successfully")
        
    except ImportError as e:
        print(f"❌ Failed to import RailwayArticleBot: {e}")
        return False
    
    print("\n✅ All imports successful!")
    return True

async def test_api_client():
    """Test API client functionality"""
    print("\n🔌 Testing API client...")
    
    try:
        from railway_api_client import RailwayAPIClient
        
        client = RailwayAPIClient()
        print("✅ RailwayAPIClient created successfully")
        
        # Test connection
        print("🌐 Testing connection...")
        connection_status = await client.test_connection()
        print(f"✅ Connection test completed: {connection_status}")
        
        return True
        
    except Exception as e:
        print(f"❌ API client test failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Railway Bot Configuration Test")
    print("=" * 50)
    
    # Test configuration
    config_ok = test_config()
    
    if not config_ok:
        print("\n❌ Configuration test failed!")
        return False
    
    # Test API client
    print("\n" + "=" * 50)
    api_ok = asyncio.run(test_api_client())
    
    if not api_ok:
        print("\n❌ API client test failed!")
        return False
    
    print("\n🎉 All tests passed!")
    print("\n📝 Next steps:")
    print("1. Set ARTICLE_BOT_TOKEN in environment")
    print("2. Run: python run_railway_bot.py")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
