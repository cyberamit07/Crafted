from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.database import get_session
from database.models import DealStatus
from database.repositories import DealRepository, DisputeRepository, LogRepository, UserRepository
from config import config
from utils.helpers import format_deal_id, get_username_display

router = Router()

class DisputeState(StatesGroup):
    waiting_for_reason = State()

@router.callback_query(F.data.startswith("dispute_"))
async def start_dispute(callback: CallbackQuery, state: FSMContext, db_user):
    """Start a dispute"""
    deal_id = callback.data.split("_")[1]
    
    async for session in get_session():
        deal_repo = DealRepository(session)
        deal = await deal_repo.get_by_id(deal_id)
        
        if not deal:
            await callback.answer("Deal not found!", show_alert=True)
            return
        
        # Check if user is participant
        participant = await deal_repo.get_deal_participants(deal.id)
        if not participant:
            await callback.answer("You are not a participant.", show_alert=True)
            return
        
        user_id = db_user.id
        if participant.buyer_id != user_id and participant.seller_id != user_id:
            await callback.answer("You are not a participant.", show_alert=True)
            return
        
        # Check if deal is active
        if deal.status != DealStatus.ACTIVE:
            await callback.answer("Deal is not active.", show_alert=True)
            return
        
        # Check if dispute already exists
        from sqlalchemy import select
        from database.models import Dispute, DisputeStatus
        result = await session.execute(
            select(Dispute).where(Dispute.deal_id == deal.id)
            .where(Dispute.status == DisputeStatus.OPEN)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            await callback.answer("A dispute is already open for this deal.", show_alert=True)
            return
        
        await state.set_state(DisputeState.waiting_for_reason)
        await state.update_data(deal_id=deal_id)
        
        await callback.message.edit_text(
            f"⚠️ <b>Dispute Initiation</b>\n\n"
            f"Deal: {format_deal_id(deal_id)}\n\n"
            f"Please explain the reason for this dispute:\n\n"
            f"<i>Type your reason below. Send 'cancel' to cancel.</i>"
        )
        await callback.answer()
        break

@router.message(DisputeState.waiting_for_reason)
async def process_dispute_reason(message: Message, state: FSMContext, db_user):
    """Process dispute reason"""
    if message.text.lower() == 'cancel':
        await state.clear()
        await message.reply("❌ Dispute cancelled.")
        return
    
    data = await state.get_data()
    deal_id = data.get('deal_id')
    
    async for session in get_session():
        deal_repo = DealRepository(session)
        deal = await deal_repo.get_by_id(deal_id)
        
        if not deal:
            await message.reply("❌ Deal not found.")
            await state.clear()
            return
        
        # Create dispute
        dispute_repo = DisputeRepository(session)
        dispute = await dispute_repo.create_dispute(
            deal.id,
            db_user.id,
            message.text
        )
        
        # Update deal status
        await deal_repo.update_status(deal.id, DealStatus.DISPUTED)
        
        # Log
        log_repo = LogRepository(session)
        await log_repo.add_log(
            'DISPUTE_OPENED',
            deal.deal_id,
            db_user.telegram_id,
            db_user.username,
            f"Dispute opened by {get_username_display(db_user)}"
        )
        
        await session.commit()
        
        # Notify staff
        await notify_staff_dispute(message.bot, deal, dispute, db_user)
        
        await message.reply(
            f"⚠️ <b>Dispute Created!</b>\n\n"
            f"Deal: {format_deal_id(deal_id)}\n\n"
            f"Your dispute has been recorded.\n"
            f"Staff has been notified and will review it."
        )
        
        await state.clear()
        break

async def notify_staff_dispute(bot, deal, dispute, user):
    """Notify staff about dispute"""
    # Get all escrowers and admins
    async for session in get_session():
        from database.repositories import EscrowerRepository, AdminRepository
        escrower_repo = EscrowerRepository(session)
        admin_repo = AdminRepository(session)
        
        escrowers = await escrower_repo.get_all_escrowers()
        admins = await admin_repo.get_all_admins()
        
        message = (
            f"⚠️ <b>New Dispute</b>\n\n"
            f"Deal: {format_deal_id(deal.deal_id)}\n"
            f"Initiated by: {get_username_display(user)}\n\n"
            f"<b>Reason:</b>\n{dispute.reason}\n\n"
            f"Please review and take appropriate action."
        )
        
        # Send to owner
        await bot.send_message(config.OWNER_ID, message)
        
        # Send to escrowers
        for escrower in escrowers:
            try:
                await bot.send_message(escrower.user.telegram_id, message)
            except:
                pass
        
        # Send to admins
        for admin in admins:
            try:
                await bot.send_message(admin.user.telegram_id, message)
            except:
                pass
        break
