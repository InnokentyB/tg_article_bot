#!/usr/bin/env python3
"""
Test script to check bot connection
"""
import asyncio
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv('ARTICLE_BOT_TOKEN')

def test_bot_info():
    """Test bot info via Telegram API"""
    print("🤖 Testing bot connection...")
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data['result']
                print("✅ Bot connection successful!")
                print(f"📱 Bot name: {bot_info.get('first_name')}")
                print(f"👤 Username: @{bot_info.get('username')}")
                print(f"🆔 Bot ID: {bot_info.get('id')}")
                return True
            else:
                print(f"❌ Bot API error: {data.get('description')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def test_webhook_info():
    """Test webhook info"""
    print("\n🔗 Testing webhook info...")
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                webhook_info = data['result']
                print("✅ Webhook info retrieved!")
                print(f"🔗 URL: {webhook_info.get('url', 'Not set')}")
                print(f"📊 Pending updates: {webhook_info.get('pending_update_count', 0)}")
                print(f"⏰ Last error: {webhook_info.get('last_error_date', 'None')}")
                return True
            else:
                print(f"❌ Webhook API error: {data.get('description')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def delete_webhook():
    """Delete webhook to enable polling"""
    print("\n🗑️ Deleting webhook...")
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print("✅ Webhook deleted successfully!")
                return True
            else:
                print(f"❌ Webhook deletion error: {data.get('description')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting bot connection tests...\n")
    
    # Test bot info
    if test_bot_info():
        # Test webhook info
        test_webhook_info()
        
        # Delete webhook
        delete_webhook()
        
        print("\n✅ All tests completed!")
        print("📱 Bot is ready to receive messages!")
        print("🔗 You can now message your bot on Telegram")
    else:
        print("\n❌ Bot connection failed!")
        print("🔧 Please check your bot token in .env file")
