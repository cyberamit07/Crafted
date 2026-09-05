import logging
from typing import Optional
from datetime import datetime
from aiogram import Bot

from config import config
from database.database import get_session
from database.repositories import LogRepository
from utils.helpers import format_timestamp, get_username_display

logger = logging.getLogger(__name__)

class LoggingService:
    """Service for handling logs"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def log_action(self, action: str, user_id: int = None, 
                         username: str = None, deal_id: str = None,
                         details: str = None, log_channel: bool = True):
        """Log an action"""
        # Save to database
        async for session in get_session():
            log_repo = LogRepository(session)
            log = await log_repo.add_log(
                action=action,
                deal_id=deal_id,
                user_id=user_id,
                username=username,
                details=details
            )
            await session.commit()
            break
        
        # Send to log channel if enabled
        if log_channel and config.LOG_CHANNEL_ID:
            try:
                await self._send_to_log_channel(log)
            except Exception as e:
                logger.error(f"Failed to send log to channel: {e}")
    
    async def _send_to_log_channel(self, log):
        """Send log to channel"""
        action_display = {
            'DEAL_CREATED': '📝 Deal Created',
            'DEAL_AGREED': '✅ Deal Agreed',
            'DEAL_CANCELLED': '❌ Deal Cancelled',
            'PAYMENT_RECEIVED': '💰 Payment Received',
            'DEAL_COMPLETED': '✅ Deal Completed',
            'REFUND_PROCESSED': '↩️ Refund Processed',
            'DISPUTE_OPENED': '⚠️ Dispute Opened',
            'ESCROWER_ADDED': '🛡 Escrower Added',
            'ESCROWER_REMOVED': '🛡 Escrower Removed',
            'ADMIN_ADDED': '🔧 Admin Added',
            'ADMIN_REMOVED': '🔧 Admin Removed',
            'USER_BANNED': '🚫 User Banned',
            'USER_UNBANNED': '✅ User Unbanned'
        }
        
        action_text = action_display.get(log.action, log.action)
        
        message = (
            f"📋 <b>DEAL LOG</b>\n\n"
            f"<b>Action:</b> {action_text}\n"
        )
        
        if log.deal_id:
            message += f"<b>Deal ID:</b> #{log.deal_id}\n"
        
        if log.user_id:
            message += f"<b>User ID:</b> {log.user_id}\n"
        
        if log.username:
            message += f"<b>Username:</b> @{log.username}\n"
        
        if log.details:
            message += f"\n<b>Details:</b>\n{log.details}\n"
        
        message += f"\n<b>Time:</b> {format_timestamp(log.created_at)}"
        
        try:
            await self.bot.send_message(
                config.LOG_CHANNEL_ID,
                message
            )
        except Exception as e:
            logger.error(f"Failed to send log to channel: {e}")
