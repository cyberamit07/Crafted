from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from database.database import get_session
from database.models import DealStatus
from database.repositories import DealRepository, LogRepository, UserRepository
from services.logging_service import LoggingService
from utils.helpers import format_deal_id, get_username_display, parse_deal_id

router = Router()

@router.message(Command("add"))
async def cmd_add(message: Message, is_staff: bool, db_user):
    """Mark payment as received (Escrower/Owner only)"""
    if not is_staff:
        await message.reply("⚠️ Only staff members can use this command.")
        return
    
    # Check if replying to a message
    if not message.reply_to_message:
        await message.reply(
            "⚠️ Please reply to the deal message with /add\n\n"
            "Example: Reply to the deal creation message with /add"
        )
        return
    
    # Extract deal ID from replied message
    replied_text = message.reply_to_message.text or message.reply_to_message.caption
    deal_id = parse_deal_id(replied_text or "")
    
    if not deal_id:
        await message.reply(
            "⚠️ Could not find deal ID in replied message.\n"
            "Please reply to a valid deal message."
        )
        return
    
    async for session in get_session():
        deal_repo = DealRepository(session)
        deal = await deal_repo.get_by_id(deal_id)
        
        if not deal:
            await message.reply(f"❌ Deal {format_deal_id(deal_id)} not found.")
            return
        
        # Check deal status
        if deal.status != DealStatus.AGREED_WAITING_PAYMENT:
            await message.reply(
                f"⚠️ Deal {format_deal_id(deal_id)} is not waiting for payment.\n"
                f"Current status: {deal.status.value}"
            )
            return
        
        # Check if payment already received
        if deal.payments:
            payment = deal.payments[0]
            if payment.is_received:
                await message.reply(
                    f"⚠️ Payment for {format_deal_id(deal_id)} already marked as received."
                )
                return
        
        # Assign escrower if not assigned
        if not deal.escrower_id:
            await deal_repo.assign_escrower(deal.id, db_user.id)
            deal = await deal_repo.get_by_id(deal_id)  # Refresh
        
        # Create payment record
        from database.models import Payment
        payment = Payment(
            deal_id=deal.id,
            amount=deal.amount,
            payment_method=deal.payment_method,
            is_received=True,
            received_at=datetime.utcnow(),
            confirmed_by=db_user.id
        )
        session.add(payment)
        
        # Update deal status
        await deal_repo.update_status(deal.id, DealStatus.ACTIVE)
        
        # Log
        log_repo = LogRepository(session)
        await log_repo.add_log(
            'PAYMENT_RECEIVED',
            deal.deal_id,
            db_user.telegram_id,
            db_user.username,
            f"Payment received by {get_username_display(db_user)}"
        )
        
        await session.commit()
        
        # Get participants
        participant = await deal_repo.get_deal_participants(deal.id)
        
        # Send notification
        buyer_mention = f"[Buyer](tg://user?id={participant.buyer.telegram_id})"
        seller_mention = f"[Seller](tg://user?id={participant.seller.telegram_id})"
        
        notification = (
            f"#Crafted_Escrow\n\n"
            f"💰 <b>Payment Received</b>\n\n"
            f"Deal ID: {format_deal_id(deal.deal_id)}\n\n"
            f"<b>Buyer:</b> {buyer_mention}\n"
            f"<b>Seller:</b> {seller_mention}\n\n"
            f"<b>Amount:</b> {deal.amount} {deal.payment_method.name}\n"
            f"<b>Payment:</b> {deal.payment_method.name}\n"
            f"<b>Holding Time:</b> {deal.holding_time}\n\n"
            f"🔒 <b>Escrow deal is now active.</b>\n\n"
            f"<b>Escrower:</b> {get_username_display(db_user)}"
        )
        
        # Notify participants
        try:
            await message.bot.send_message(participant.buyer.telegram_id, notification)
        except:
            pass
        try:
            await message.bot.send_message(participant.seller.telegram_id, notification)
        except:
            pass
        
        await message.reply(
            f"✅ <b>Payment Received!</b>\n\n"
            f"{format_deal_id(deal.deal_id)}\n\n"
            f"Deal is now <b>ACTIVE</b>.\n"
            f"Buyer and seller have been notified."
        )
        break

@router.message(Command("done"))
async def cmd_done(message: Message, is_staff: bool, db_user):
    """Complete a deal (Escrower/Owner only)"""
    if not is_staff:
        await message.reply("⚠️ Only staff members can use this command.")
        return
    
    if not message.reply_to_message:
        await message.reply(
            "⚠️ Please reply to the payment message with /done\n\n"
            "Example: Reply to the 'Payment Received' message with /done"
        )
        return
    
    # Extract deal ID
    replied_text = message.reply_to_message.text or message.reply_to_message.caption
    deal_id = parse_deal_id(replied_text or "")
    
    if not deal_id:
        await message.reply("⚠️ Could not find deal ID in replied message.")
        return
    
    async for session in get_session():
        deal_repo = DealRepository(session)
        deal = await deal_repo.get_by_id(deal_id)
        
        if not deal:
            await message.reply(f"❌ Deal {format_deal_id(deal_id)} not found.")
            return
        
        # Check if deal is active
        if deal.status != DealStatus.ACTIVE:
            await message.reply(
                f"⚠️ Deal {format_deal_id(deal_id)} is not active.\n"
                f"Current status: {deal.status.value}"
            )
            return
        
        # Check if payment was received
        if not deal.payments or not deal.payments[0].is_received:
            await message.reply(
                f"⚠️ Payment for {format_deal_id(deal_id)} has not been received yet."
            )
            return
        
        # Mark as completed
        await deal_repo.update_status(deal.id, DealStatus.COMPLETED)
        
        # Log
        log_repo = LogRepository(session)
        await log_repo.add_log(
            'DEAL_COMPLETED',
            deal.deal_id,
            db_user.telegram_id,
            db_user.username,
            f"Deal completed by {get_username_display(db_user)}"
        )
        
        await session.commit()
        
        # Get participants
        participant = await deal_repo.get_deal_participants(deal.id)
        
        # Send completion notification
        completion_message = (
            f"#Crafted_Escrow\n\n"
            f"✅ <b>Safe Escrow Deal Completed</b>\n\n"
            f"Deal ID: {format_deal_id(deal.deal_id)}\n\n"
            f"<b>Buyer:</b> {get_username_display(participant.buyer)}\n"
            f"<b>Seller:</b> {get_username_display(participant.seller)}\n\n"
            f"<b>Amount:</b> {deal.amount} {deal.payment_method.name}\n"
            f"<b>Payment:</b> {deal.payment_method.name}\n\n"
            f"🛡 <b>Escrower:</b> {get_username_display(db_user)}\n\n"
            f"✅ Deal successfully completed."
        )
        
        # Notify participants
        for user_id in [participant.buyer.telegram_id, participant.seller.telegram_id]:
            try:
                await message.bot.send_message(user_id, completion_message)
            except:
                pass
        
        # Request vouches
        await request_vouches(message.bot, deal, participant)
        
        await message.reply(
            f"✅ <b>Deal Completed!</b>\n\n"
            f"{format_deal_id(deal.deal_id)}\n\n"
            f"Vouch requests sent to both parties."
        )
        break

async def request_vouches(bot, deal, participant):
    """Request vouches from both parties"""
    vouch_message = (
        f"⭐ <b>Vouch Request</b>\n\n"
        f"Deal: {format_deal_id(deal.deal_id)}\n\n"
        f"Please send your vouch for this deal.\n"
        f"Share your experience with the transaction.\n\n"
        f"<i>Reply to this message with your vouch.</i>"
    )
    
    # Send to buyer
    try:
        buyer_msg = await bot.send_message(
            participant.buyer.telegram_id,
            vouch_message
        )
        # Store message for vouch collection
        async for session in get_session():
            from database.repositories import VouchRepository
            vouch_repo = VouchRepository(session)
            await vouch_repo.create_vouch(
                deal.id,
                participant.buyer.id,
                "Waiting for vouch..."
            )
            break
    except:
        pass
    
    # Send to seller
    try:
        seller_msg = await bot.send_message(
            participant.seller.telegram_id,
            vouch_message
        )
        async for session in get_session():
            from database.repositories import VouchRepository
            vouch_repo = VouchRepository(session)
            await vouch_repo.create_vouch(
                deal.id,
                participant.seller.id,
                "Waiting for vouch..."
            )
            break
    except:
        pass

@router.message(Command("refund"))
async def cmd_refund(message: Message, is_staff: bool, db_user):
    """Process refund (Escrower/Owner only)"""
    if not is_staff:
        await message.reply("⚠️ Only staff members can use this command.")
        return
    
    if not message.reply_to_message:
        await message.reply(
            "⚠️ Please reply to the payment message with /refund\n\n"
            "Example: Reply to the 'Payment Received' message with /refund"
        )
        return
    
    # Extract deal ID
    replied_text = message.reply_to_message.text or message.reply_to_message.caption
    deal_id = parse_deal_id(replied_text or "")
    
    if not deal_id:
        await message.reply("⚠️ Could not find deal ID in replied message.")
        return
    
    # Ask for refund reason
    await message.reply(
        f"🔄 <b>Refund Request</b>\n\n"
        f"Deal: {format_deal_id(deal_id)}\n\n"
        f"Please enter the refund reason (or type 'cancel' to cancel):"
    )
    
    # Store deal_id for next step
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    
    class RefundState(StatesGroup):
        waiting_for_reason = State()
    
    from aiogram.fsm.context import FSMContext
    state = FSMContext()
    await state.set_state(RefundState.waiting_for_reason)
    await state.update_data(deal_id=deal_id)

# Need to handle the refund reason in another handler
# This will be continued in the next file
