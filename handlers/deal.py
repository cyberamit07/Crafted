from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from database.database import get_session
from database.models import DealStatus, PaymentMethod
from database.repositories import DealRepository, UserRepository, LogRepository
from services.logging_service import LoggingService
from keyboards.deal import get_deal_form_keyboard, get_agreement_keyboard
from utils.helpers import format_deal_id, format_amount, get_username_display, format_timestamp
from config import config

router = Router()

class DealForm(StatesGroup):
    """States for deal creation"""
    waiting_for_buyer = State()
    waiting_for_seller = State()
    waiting_for_item = State()
    waiting_for_amount = State()
    waiting_for_payment = State()
    waiting_for_holding = State()
    waiting_for_terms = State()
    waiting_for_confirmation = State()

@router.message(F.text == "🤝 Create Deal")
async def start_deal_creation(message: Message, state: FSMContext, db_user):
    """Start deal creation process"""
    await state.set_state(DealForm.waiting_for_buyer)
    await message.reply(
        "📝 <b>Deal Form</b>\n\n"
        "Please enter the <b>Buyer's Telegram ID</b> (numeric ID):\n\n"
        "You can get this by forwarding a message from them or using @userinfobot.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_deal")]
        ])
    )

@router.callback_query(F.data == "cancel_deal")
async def cancel_deal(callback: CallbackQuery, state: FSMContext):
    """Cancel deal creation"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Deal creation cancelled.")
    await callback.answer()

@router.message(DealForm.waiting_for_buyer)
async def process_buyer(message: Message, state: FSMContext):
    """Process buyer ID"""
    try:
        buyer_id = int(message.text.strip())
        await state.update_data(buyer_id=buyer_id)
        await state.set_state(DealForm.waiting_for_seller)
        
        # Verify buyer exists
        async for session in get_session():
            user_repo = UserRepository(session)
            buyer = await user_repo.get_by_telegram_id(buyer_id)
            if not buyer:
                await message.reply(
                    "⚠️ Buyer not found in database. They need to start the bot first.\n"
                    "Please ask them to send /start to the bot.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Retry", callback_data="retry_buyer")],
                        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_deal")]
                    ])
                )
                return
            await state.update_data(buyer_username=get_username_display(buyer))
            break
        
        await message.reply(
            f"✅ Buyer set: {message.text}\n\n"
            "Please enter the <b>Seller's Telegram ID</b> (numeric ID):"
        )
    except ValueError:
        await message.reply("⚠️ Please enter a valid numeric Telegram ID.")

@router.callback_query(F.data == "retry_buyer")
async def retry_buyer(callback: CallbackQuery, state: FSMContext):
    """Retry entering buyer"""
    await state.set_state(DealForm.waiting_for_buyer)
    await callback.message.edit_text(
        "Please enter the <b>Buyer's Telegram ID</b> (numeric ID):"
    )
    await callback.answer()

@router.message(DealForm.waiting_for_seller)
async def process_seller(message: Message, state: FSMContext):
    """Process seller ID"""
    try:
        seller_id = int(message.text.strip())
        data = await state.get_data()
        buyer_id = data.get('buyer_id')
        
        if seller_id == buyer_id:
            await message.reply("⚠️ Buyer and seller cannot be the same person.")
            return
        
        await state.update_data(seller_id=seller_id)
        await state.set_state(DealForm.waiting_for_item)
        
        # Verify seller exists
        async for session in get_session():
            user_repo = UserRepository(session)
            seller = await user_repo.get_by_telegram_id(seller_id)
            if not seller:
                await message.reply(
                    "⚠️ Seller not found in database. They need to start the bot first.\n"
                    "Please ask them to send /start to the bot."
                )
                return
            await state.update_data(seller_username=get_username_display(seller))
            break
        
        await message.reply(
            f"✅ Seller set: {message.text}\n\n"
            "Please enter the <b>Item/Service</b> description:"
        )
    except ValueError:
        await message.reply("⚠️ Please enter a valid numeric Telegram ID.")

@router.message(DealForm.waiting_for_item)
async def process_item(message: Message, state: FSMContext):
    """Process item description"""
    await state.update_data(item=message.text.strip())
    await state.set_state(DealForm.waiting_for_amount)
    await message.reply(
        "Please enter the <b>Amount</b> (number only):\n\n"
        "Example: 500"
    )

@router.message(DealForm.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    """Process amount"""
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
        await state.update_data(amount=amount)
        await state.set_state(DealForm.waiting_for_payment)
        
        # Payment method selection
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇮🇳 INR", callback_data="payment_INR")],
            [InlineKeyboardButton(text="💎 GRAM", callback_data="payment_GRAM")],
            [InlineKeyboardButton(text="💵 USDT", callback_data="payment_USDT")],
            [InlineKeyboardButton(text="⭐ STARS", callback_data="payment_STARS")]
        ])
        
        await message.reply(
            f"✅ Amount: {amount}\n\n"
            "Please select the <b>Payment Method</b>:",
            reply_markup=keyboard
        )
    except ValueError:
        await message.reply("⚠️ Please enter a valid number.")

@router.callback_query(F.data.startswith("payment_"))
async def process_payment_method(callback: CallbackQuery, state: FSMContext):
    """Process payment method selection"""
    method = callback.data.split("_")[1]
    payment_method = PaymentMethod[method]
    await state.update_data(payment_method=payment_method)
    await state.set_state(DealForm.waiting_for_holding)
    
    await callback.message.edit_text(
        f"✅ Payment method: {method}\n\n"
        "Please enter the <b>Holding Time</b>:\n\n"
        "Example: 2 hours, 1 day, 30 minutes"
    )
    await callback.answer()

@router.message(DealForm.waiting_for_holding)
async def process_holding(message: Message, state: FSMContext):
    """Process holding time"""
    await state.update_data(holding_time=message.text.strip())
    await state.set_state(DealForm.waiting_for_terms)
    await message.reply(
        "Please enter the <b>Terms & Conditions</b> (or type 'none' to skip):\n\n"
        "Include any important conditions for the deal."
    )

@router.message(DealForm.waiting_for_terms)
async def process_terms(message: Message, state: FSMContext):
    """Process terms"""
    terms = message.text.strip()
    if terms.lower() == 'none':
        terms = None
    await state.update_data(terms=terms)
    await state.set_state(DealForm.waiting_for_confirmation)
    
    # Show deal summary
    data = await state.get_data()
    summary = (
        "#Crafted_Escrow\n\n"
        "📝 <b>Deal Form</b>\n\n"
        f"<b>Buyer:</b> {data.get('buyer_username', data.get('buyer_id'))}\n"
        f"<b>Seller:</b> {data.get('seller_username', data.get('seller_id'))}\n"
        f"<b>Item:</b> {data.get('item')}\n"
        f"<b>Amount:</b> {format_amount(data.get('amount'), data.get('payment_method').name)}\n"
        f"<b>Payment:</b> {data.get('payment_method').name}\n"
        f"<b>Holding Time:</b> {data.get('holding_time')}\n"
        f"<b>Terms & Conditions:</b> {data.get('terms', 'None')}\n\n"
        "🔍 <b>Please confirm the deal details above.</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_deal"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_deal")
        ]
    ])
    
    await message.reply(summary, reply_markup=keyboard)

@router.callback_query(F.data == "confirm_deal")
async def confirm_deal(callback: CallbackQuery, state: FSMContext, db_user):
    """Create deal in database"""
    data = await state.get_data()
    
    try:
        async for session in get_session():
            # Get or create users
            user_repo = UserRepository(session)
            
            buyer = await user_repo.get_or_create(
                data.get('buyer_id'),
                None,
                "Buyer",
                None
            )
            seller = await user_repo.get_or_create(
                data.get('seller_id'),
                None,
                "Seller",
                None
            )
            
            # Create deal
            deal_repo = DealRepository(session)
            deal = await deal_repo.create_deal(
                buyer.id,
                seller.id,
                data.get('item'),
                data.get('amount'),
                data.get('payment_method'),
                data.get('holding_time'),
                data.get('terms')
            )
            
            # Log deal creation
            log_repo = LogRepository(session)
            await log_repo.add_log(
                'DEAL_CREATED',
                deal.deal_id,
                db_user.telegram_id,
                db_user.username,
                f"Deal created by {get_username_display(db_user)}"
            )
            
            await session.commit()
            
            # Send notification to participants
            buyer_mention = f"[Buyer](tg://user?id={data.get('buyer_id')})"
            seller_mention = f"[Seller](tg://user?id={data.get('seller_id')})"
            
            deal_message = (
                f"📝 <b>New Deal Created!</b>\n\n"
                f"{format_deal_id(deal.deal_id)}\n\n"
                f"<b>Item:</b> {deal.item}\n"
                f"<b>Amount:</b> {format_amount(deal.amount, deal.payment_method.name)}\n"
                f"<b>Payment:</b> {deal.payment_method.name}\n"
                f"<b>Holding Time:</b> {deal.holding_time}\n\n"
                f"<b>Buyer:</b> {buyer_mention}\n"
                f"<b>Seller:</b> {seller_mention}\n\n"
                "⏳ <b>Waiting for both parties to agree.</b>"
            )
            
            # Send to participants
            agreement_keyboard = get_agreement_keyboard(deal.deal_id)
            
            await callback.bot.send_message(
                data.get('buyer_id'),
                deal_message,
                reply_markup=agreement_keyboard
            )
            await callback.bot.send_message(
                data.get('seller_id'),
                deal_message,
                reply_markup=agreement_keyboard
            )
            
            await callback.message.edit_text(
                f"✅ <b>Deal Created!</b>\n\n"
                f"{format_deal_id(deal.deal_id)}\n\n"
                "The buyer and seller have been notified. "
                "Both parties must agree to proceed."
            )
            
            await state.clear()
            await callback.answer()
            break
            
    except Exception as e:
        await callback.message.edit_text(
            "❌ <b>Error creating deal.</b>\n\n"
            f"Error: {str(e)}\n\n"
            "Please try again or contact support."
        )
        await callback.answer()

@router.callback_query(F.data.startswith("agree_"))
async def handle_agreement(callback: CallbackQuery, db_user):
    """Handle agreement from buyer or seller"""
    deal_id = callback.data.split("_")[1]
    
    async for session in get_session():
        deal_repo = DealRepository(session)
        
        # Verify deal exists
        deal = await deal_repo.get_by_id(deal_id)
        if not deal:
            await callback.answer("Deal not found!", show_alert=True)
            return
        
        # Check if deal is in correct state
        if deal.status != DealStatus.WAITING_FOR_AGREEMENT:
            await callback.answer("This deal is no longer waiting for agreement.", show_alert=True)
            return
        
        # Check if user is participant
        participant = await deal_repo.get_deal_participants(deal.id)
        if not participant:
            await callback.answer("You are not a participant in this deal.", show_alert=True)
            return
        
        user_id = db_user.id
        if participant.buyer_id != user_id and participant.seller_id != user_id:
            await callback.answer("You are not a participant in this deal.", show_alert=True)
            return
        
        # Check if already agreed
        if participant.buyer_id == user_id and participant.buyer_agreed:
            await callback.answer("You have already agreed to this deal.", show_alert=True)
            return
        if participant.seller_id == user_id and participant.seller_agreed:
            await callback.answer("You have already agreed to this deal.", show_alert=True)
            return
        
        # Set agreement
        await deal_repo.set_agreement(deal.id, user_id, True)
        
        # Check if both agreed
        updated_participant = await deal_repo.get_deal_participants(deal.id)
        if updated_participant.buyer_agreed and updated_participant.seller_agreed:
            deal.status = DealStatus.AGREED_WAITING_PAYMENT
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ <b>Both parties have agreed!</b>\n\n"
                f"{format_deal_id(deal_id)}\n\n"
                "Payment verification will be handled by an escrower.\n"
                "Please wait for an escrower to confirm payment."
            )
            
            # Notify both parties
            message = (
                f"✅ <b>Deal Agreed!</b>\n\n"
                f"{format_deal_id(deal_id)}\n\n"
                "Both parties have agreed to the terms.\n"
                "Waiting for payment verification."
            )
            
            await callback.bot.send_message(participant.buyer_id, message)
            await callback.bot.send_message(participant.seller_id, message)
            
            # Notify staff
            await notify_staff(callback.bot, deal_id, "Deal agreed by both parties")
        else:
            await callback.message.edit_text(
                f"✅ <b>You have agreed!</b>\n\n"
                f"{format_deal_id(deal_id)}\n\n"
                "Waiting for the other party to agree."
            )
        
        await callback.answer()

async def notify_staff(bot, deal_id: str, message: str):
    """Notify staff about important events"""
    try:
        # Get all escrowers and admins
        async for session in get_session():
            from database.repositories import EscrowerRepository, AdminRepository
            escrower_repo = EscrowerRepository(session)
            admin_repo = AdminRepository(session)
            
            escrowers = await escrower_repo.get_all_escrowers()
            admins = await admin_repo.get_all_admins()
            
            # Send to owner as well
            await bot.send_message(
                config.OWNER_ID,
                f"📢 <b>Staff Notification</b>\n\n"
                f"Deal: {format_deal_id(deal_id)}\n"
                f"{message}"
            )
            
            # Send to escrowers
            for escrower in escrowers:
                try:
                    await bot.send_message(
                        escrower.user.telegram_id,
                        f"📢 <b>Staff Notification</b>\n\n"
                        f"Deal: {format_deal_id(deal_id)}\n"
                        f"{message}"
                    )
                except:
                    pass
            
            # Send to admins
            for admin in admins:
                try:
                    await bot.send_message(
                        admin.user.telegram_id,
                        f"📢 <b>Staff Notification</b>\n\n"
                        f"Deal: {format_deal_id(deal_id)}\n"
                        f"{message}"
                    )
                except:
                    pass
            break
    except Exception as e:
        logging.error(f"Error notifying staff: {e}")
