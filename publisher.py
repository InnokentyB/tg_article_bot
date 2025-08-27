"""
Telegram publishing functionality
"""
import logging
import requests
import os
from datetime import datetime
import html

logger = logging.getLogger(__name__)

class TelegramPublisher:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
        if not self.token or not self.chat_id:
            logger.error("Telegram token or chat ID not configured")
    
    def publish_article(self, article):
        """Publish article review to Telegram"""
        try:
            if not self.token or not self.chat_id:
                logger.error("Telegram not configured, skipping publication")
                return False
            
            # Format message
            message = self._format_message(article)
            
            # Send message
            return self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error publishing article: {str(e)}")
            return False
    
    def _format_message(self, article):
        """Format article for Telegram message"""
        try:
            title = html.escape(article.get('title', 'Без названия'))
            url = article.get('url', '')
            review = article.get('summary', '')
            category = article.get('category', '')
            
            # Create category emoji mapping
            category_emojis = {
                'ai_ml': '🤖',
                'system_design': '🏗️',
                'programming': '💻',
                'devops': '⚙️',
                'data': '📊',
                'tech_trends': '🚀',
                'irrelevant': '📝'
            }
            
            emoji = category_emojis.get(category, '📝')
            
            # Format message
            message = f"{emoji} <b>{title}</b>\n\n"
            
            if review:
                message += f"{review}\n\n"
            
            message += f"<a href=\"{url}\">Читать полностью</a>"
            
            # Add category tag if needed
            if category and category != 'irrelevant':
                hashtag = f"#{category.replace('_', '')}"
                message += f"\n\n{hashtag}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting message: {str(e)}")
            return f"Новая статья: {article.get('title', 'Без названия')}\n{article.get('url', '')}"
    
    def _send_message(self, message, parse_mode='HTML'):
        """Send message to Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False,
                'disable_notification': False
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info("Message sent successfully to Telegram")
                    return True
                else:
                    logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
                    return False
            else:
                logger.error(f"HTTP error sending message: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message: {str(e)}")
            return False
    
    def send_test_message(self):
        """Send a test message to verify configuration"""
        try:
            test_message = f"🧪 Тест RSS бота\n\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nБот работает корректно!"
            
            return self._send_message(test_message)
            
        except Exception as e:
            logger.error(f"Error sending test message: {str(e)}")
            return False
    
    def get_chat_info(self):
        """Get information about the chat"""
        try:
            url = f"{self.base_url}/getChat"
            data = {'chat_id': self.chat_id}
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    return result.get('result', {})
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting chat info: {str(e)}")
            return None
    
    def validate_configuration(self):
        """Validate Telegram bot configuration"""
        try:
            if not self.token:
                return False, "Telegram token not configured"
            
            if not self.chat_id:
                return False, "Telegram chat ID not configured"
            
            # Test bot token
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return False, f"Invalid bot token or network error: {response.status_code}"
            
            result = response.json()
            if not result.get('ok'):
                return False, f"Bot token validation failed: {result.get('description', 'Unknown error')}"
            
            # Test chat access
            chat_info = self.get_chat_info()
            if not chat_info:
                return False, "Cannot access specified chat - check chat ID and bot permissions"
            
            bot_info = result.get('result', {})
            bot_name = bot_info.get('username', 'Unknown')
            
            return True, f"Configuration valid. Bot: @{bot_name}, Chat: {chat_info.get('title', chat_info.get('username', 'Unknown'))}"
            
        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"
