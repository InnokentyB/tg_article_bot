"""
Telegram reactions and message tracking system
"""
import logging
from typing import Dict, List, Optional
from aiogram import types
from aiogram.types import MessageReactionUpdated, MessageReactionCountUpdated
from database import DatabaseManager

logger = logging.getLogger(__name__)

class TelegramReactionsTracker:
    """Handles Telegram message reactions and statistics"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
        # Emoji mapping for better display
        self.emoji_names = {
            '👍': 'like',
            '👎': 'dislike', 
            '❤️': 'love',
            '🔥': 'fire',
            '😍': 'wow',
            '😂': 'laugh',
            '😢': 'sad',
            '😡': 'angry',
            '🎉': 'celebrate',
            '🤔': 'think'
        }
    
    async def save_article_message_link(self, article_id: int, message_id: int, chat_id: int):
        """Save link between article and Telegram message"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """UPDATE articles 
                   SET telegram_message_id = $2, telegram_chat_id = $3, updated_at = CURRENT_TIMESTAMP
                   WHERE id = $1""",
                article_id, message_id, chat_id
            )
        
        logger.info(f"Linked article {article_id} to message {message_id} in chat {chat_id}")
    
    async def handle_message_reaction(self, reaction: MessageReactionUpdated):
        """Handle individual message reactions (private chats/groups)"""
        try:
            message_id = reaction.message_id
            chat_id = reaction.chat.id
            user_id = reaction.user.id if reaction.user else None
            
            # Find article linked to this message
            article = await self.find_article_by_message(message_id, chat_id)
            if not article:
                logger.warning(f"No article found for message {message_id}")
                return
                
            article_id = article['id']
            
            # Process new reactions
            new_reactions = reaction.new_reaction or []
            old_reactions = reaction.old_reaction or []
            
            # Track changes
            for reaction_obj in new_reactions:
                if reaction_obj not in old_reactions:
                    await self.add_reaction(article_id, user_id, reaction_obj.emoji)
            
            for reaction_obj in old_reactions:
                if reaction_obj not in new_reactions:
                    await self.remove_reaction(article_id, user_id, reaction_obj.emoji)
                    
            logger.info(f"Updated reactions for article {article_id}")
            
        except Exception as e:
            logger.error(f"Error handling message reaction: {e}")
    
    async def handle_message_reaction_count(self, reaction_count: MessageReactionCountUpdated):
        """Handle anonymous reaction counts (channels)"""
        try:
            message_id = reaction_count.message_id
            chat_id = reaction_count.chat.id
            
            # Find article linked to this message
            article = await self.find_article_by_message(message_id, chat_id)
            if not article:
                logger.warning(f"No article found for message {message_id}")
                return
                
            article_id = article['id']
            
            # Update reaction counts in article stats
            reaction_stats = {}
            for reaction in reaction_count.reactions:
                emoji = reaction.type.emoji if hasattr(reaction.type, 'emoji') else 'unknown'
                reaction_stats[emoji] = reaction.total_count
            
            await self.update_article_reaction_stats(article_id, reaction_stats)
            logger.info(f"Updated reaction counts for article {article_id}: {reaction_stats}")
            
        except Exception as e:
            logger.error(f"Error handling reaction count: {e}")
    
    async def find_article_by_message(self, message_id: int, chat_id: int) -> Optional[Dict]:
        """Find article by Telegram message ID and chat ID"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.db.pool.acquire() as conn:
            article = await conn.fetchrow(
                """SELECT id, title, telegram_message_id, telegram_chat_id 
                   FROM articles 
                   WHERE telegram_message_id = $1 AND telegram_chat_id = $2""",
                message_id, chat_id
            )
            return dict(article) if article else None
    
    async def add_reaction(self, article_id: int, user_id: Optional[int], emoji: str):
        """Add or update user reaction to article"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO article_reactions (article_id, telegram_user_id, reaction_emoji)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (article_id, telegram_user_id, reaction_type)
                   DO UPDATE SET reaction_emoji = $3, created_at = CURRENT_TIMESTAMP""",
                article_id, user_id, emoji
            )
    
    async def remove_reaction(self, article_id: int, user_id: Optional[int], emoji: str):
        """Remove user reaction from article"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """DELETE FROM article_reactions 
                   WHERE article_id = $1 AND telegram_user_id = $2 AND reaction_emoji = $3""",
                article_id, user_id, emoji
            )
    
    async def update_article_reaction_stats(self, article_id: int, reaction_stats: Dict[str, int]):
        """Update article's reaction statistics"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
            
        # Calculate total likes from positive reactions
        likes_count = sum(count for emoji, count in reaction_stats.items() 
                         if emoji in ['👍', '❤️', '🔥', '😍', '🎉'])
        
        # Store detailed stats in external_stats JSON field
        stats_update = {
            'telegram_reactions': reaction_stats,
            'last_reaction_update': str(datetime.now())
        }
        
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """UPDATE articles 
                   SET likes_count = $2, 
                       external_stats = COALESCE(external_stats, '{}'::jsonb) || $3::jsonb,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = $1""",
                article_id, likes_count, json.dumps(stats_update)
            )
    
    async def get_article_reactions(self, article_id: int) -> Dict:
        """Get all reactions for an article"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.db.pool.acquire() as conn:
            # Get individual reactions
            reactions = await conn.fetch(
                """SELECT reaction_emoji, telegram_user_id, created_at
                   FROM article_reactions 
                   WHERE article_id = $1
                   ORDER BY created_at DESC""",
                article_id
            )
            
            # Get article's external stats
            article = await conn.fetchrow(
                """SELECT external_stats, likes_count, views_count
                   FROM articles WHERE id = $1""",
                article_id
            )
            
            # Count reactions by emoji
            reaction_counts = {}
            for reaction in reactions:
                emoji = reaction['reaction_emoji']
                reaction_counts[emoji] = reaction_counts.get(emoji, 0) + 1
            
            return {
                'individual_reactions': [dict(r) for r in reactions],
                'reaction_counts': reaction_counts,
                'total_likes': article['likes_count'] if article else 0,
                'total_views': article['views_count'] if article else 0,
                'external_stats': article['external_stats'] if article else {}
            }
    
    async def get_message_info(self, article_id: int) -> Optional[Dict]:
        """Get Telegram message info for an article"""
        if not self.db.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.db.pool.acquire() as conn:
            article = await conn.fetchrow(
                """SELECT telegram_message_id, telegram_chat_id, title
                   FROM articles WHERE id = $1""",
                article_id
            )
            
            if article and article['telegram_message_id']:
                return {
                    'message_id': article['telegram_message_id'],
                    'chat_id': article['telegram_chat_id'],
                    'title': article['title']
                }
            return None

# Import required modules at the top
import json
from datetime import datetime