from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database.database import get_session
from database.repositories import VouchRepository, DealRepository, LogRepository
from config import config
from utils.helpers import format_deal_id, get_username_display

router = Router()

@router.message(F.reply_to_message)
async def handle_vouch(message: Message):
    """Handle vouch submissions"""
    # Check if replying to a vouch request
    if not message.reply_to_message.text:
        return
    
    if "Vouch Request" not in message.reply_to_message.text:
        return
    
    # Extract deal ID
    reply_text = message.reply_to_message.text
    import re
    match = re.search(r'#CE-\d{6}', reply_text)
    if not match:
        return
    
    deal_id = match.group(0).lstrip('#')
    
    async for session in get_session():
        deal_repo = DealRepository(session)
        deal = await deal_repo.get_by_id(deal_id)
        
        if not deal:
            await message.reply("❌ Deal not found.")
            return
        
        # Check if user is a participant
        participant = await deal_repo.get_deal_participants(deal.id)
        if not participant:
            await message.reply("❌ You are not a participant in this deal.")
            return
        
        user_id = message.from_user.id
        if participant.buyer.telegram_id != user_id and participant.seller.telegram_id != user_id:
            await message.reply("❌ You are not a participant in this deal.")
            return
        
        # Save vouch
        vouch_repo = VouchRepository(session)
        
        # Check if user already vouched
        from sqlalchemy import select
        from database.models import Vouch
        result = await session.execute(
            select(Vouch).where(Vouch.deal_id == deal.id)
            .where(Vouch.user_id == participant.buyer.id if participant.buyer.telegram_id == user_id else participant.seller.id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.vouch_text = message.text
            existing.is_sent = True
            existing.sent_at = datetime.utcnow()
        else:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(user_id)
            vouch = await vouch_repo.create_vouch(
                deal.id,
                user.id,
                message.text
            )
            await vouch_repo.mark_sent(vouch.id, message.message_id)
        
        # Forward to vouch channel
        try:
            user_display = get_username_display(message.from_user)
            vouch_message = (
                f"⭐ <b>Vouch Received</b>\n\n"
                f"Deal: {format_deal_id(deal_id)}\n\n"
                f"<b>User:</b> {user_display}\n"
                f"<b>Vouch:</b>\n{message.text}"
            )
            
            await message.bot.send_message(
                config.VOUCH_CHANNEL_ID,
                vouch_message
            )
        except:
            pass
        
        # Log
        log_repo = LogRepository(session)
        await log_repo.add_log(
            'VOUCH_RECEIVED',
            deal.deal_id,
            message.from_user.id,
            message.from_user.username,
            f"Vouch received from {get_username_display(message.from_user)}"
        )
        
        await session.commit()
        
        await message.reply(
            f"✅ <b>Vouch Submitted!</b>\n\n"
            f"Thank you for your vouch for {format_deal_id(deal_id)}.\n"
            f"Your vouch has been recorded."
        )
        break
