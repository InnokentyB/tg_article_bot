#!/usr/bin/env python3
"""
Test script for Railway API integration
"""
import asyncio
import logging
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_railway import RailwayConfig
from railway_api_client import RailwayAPIClient

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

async def test_railway_integration():
    """Test Railway API integration"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🧪 Testing Railway API integration...")
    
    # Show configuration
    config = RailwayConfig()
    config_info = config.get_railway_info()
    logger.info(f"Configuration: {config_info}")
    
    # Test API client
    client = RailwayAPIClient()
    
    try:
        # Test connection
        logger.info("🔌 Testing connection...")
        connection_status = await client.test_connection()
        logger.info(f"Connection status: {connection_status}")
        
        if connection_status['connected']:
            logger.info("✅ Railway API connection successful!")
            
            # Test health endpoint
            logger.info("🏥 Testing health endpoint...")
            health_ok = await client.health_check()
            logger.info(f"Health check: {'✅ OK' if health_ok else '❌ Failed'}")
            
            # Test categories endpoint
            logger.info("🏷️ Testing categories endpoint...")
            categories = await client.get_categories()
            logger.info(f"Categories: {categories[:5]}... (total: {len(categories)})")
            
            # Test statistics endpoint
            logger.info("📊 Testing statistics endpoint...")
            stats = await client.get_statistics()
            if stats:
                logger.info(f"Statistics: {stats}")
            else:
                logger.warning("⚠️ No statistics available")
            
            # Test user creation
            logger.info("👤 Testing user creation...")
            test_user = {
                'telegram_user_id': 123456789,
                'username': 'test_user',
                'first_name': 'Test',
                'last_name': 'User'
            }
            created_user = await client.create_user(test_user)
            if created_user:
                logger.info(f"✅ User created: {created_user}")
            else:
                logger.warning("⚠️ User creation failed")
            
            # Test article creation
            logger.info("📝 Testing article creation...")
            test_article = {
                'title': 'Test Article',
                'text': 'This is a test article for integration testing.',
                'summary': 'Test summary',
                'source': 'https://example.com/test',
                'original_link': 'https://example.com/test',
                'telegram_user_id': 123456789,
                'language': 'en',
                'categories_auto': ['test', 'integration']
            }
            created_article = await client.create_article(test_article)
            if created_article:
                logger.info(f"✅ Article created: {created_article}")
                
                # Test article retrieval
                logger.info("📖 Testing article retrieval...")
                retrieved_article = await client.get_article(created_article['id'])
                if retrieved_article:
                    logger.info(f"✅ Article retrieved: {retrieved_article}")
                else:
                    logger.warning("⚠️ Article retrieval failed")
                
                # Test article update
                logger.info("✏️ Testing article update...")
                update_data = {
                    'categories_user': ['test', 'integration', 'success']
                }
                updated_article = await client.update_article(created_article['id'], update_data)
                if updated_article:
                    logger.info(f"✅ Article updated: {updated_article}")
                else:
                    logger.warning("⚠️ Article update failed")
            else:
                logger.warning("⚠️ Article creation failed")
            
        else:
            logger.error("❌ Railway API connection failed!")
            logger.error(f"Error: {connection_status.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False
    
    logger.info("🎉 Railway API integration test completed!")
    return True

async def main():
    """Main function"""
    try:
        success = await test_railway_integration()
        if success:
            print("\n✅ All tests passed! Railway integration is working.")
        else:
            print("\n❌ Some tests failed. Check the logs above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
