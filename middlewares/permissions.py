from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from database.database import get_session
from database.repositories import UserRepository, EscrowerRepository, AdminRepository
from utils.helpers import is_owner
import logging

logger = logging.getLogger(__name__)

class PermissionsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Check permissions for all events"""
        try:
            # Get user info
            if isinstance(event, Message):
                user = event.from_user
                chat = event.chat
            elif isinstance(event, CallbackQuery):
                user = event.from_user
                chat = event.message.chat if event.message else None
            else:
                return await handler(event, data)
            
            if not user:
                return await handler(event, data)
            
            # Check if user is banned
            async for session in get_session():
                user_repo = UserRepository(session)
                if await user_repo.is_banned(user.id):
                    try:
                        if isinstance(event, Message):
                            await event.reply("🚫 You are banned from using this bot.")
                        elif isinstance(event, CallbackQuery):
                            await event.answer("You are banned!", show_alert=True)
                    except TelegramBadRequest:
                        pass
                    return
                
                # Store user info in data
                db_user = await user_repo.get_or_create(
                    user.id,
                    user.username,
                    user.first_name,
                    user.last_name
                )
                
                data['db_user'] = db_user
                
                # Check if user is owner
                data['is_owner'] = await is_owner(user.id)
                
                # Check if user is admin
                admin_repo = AdminRepository(session)
                data['is_admin'] = await admin_repo.is_admin(user.id) or data['is_owner']
                
                # Check if user is escrower
                escrower_repo = EscrowerRepository(session)
                data['is_escrower'] = await escrower_repo.is_escrower(user.id)
                
                # Check staff status
                data['is_staff'] = data['is_owner'] or data['is_admin'] or data['is_escrower']
                
                break
            
            return await handler(event, data)
            
        except Exception as e:
            logger.error(f"Error in permissions middleware: {e}", exc_info=True)
            # Continue execution even on error
            return await handler(event, data)
