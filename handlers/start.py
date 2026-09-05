from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.database import get_session
from database.repositories import UserRepository, DealRepository, StatsRepository
from keyboards.user import get_main_menu_keyboard
from keyboards.deal import get_deal_status_keyboard
from utils.helpers import format_timestamp, get_username_display, format_stats

router = Router()

class HelpStates(StatesGroup):
    viewing_help = State()

@router.message(CommandStart())
async def cmd_start(message: Message, db_user, is_staff: bool):
    """Handle /start command"""
    # Register user
    async for session in get_session():
        user_repo = UserRepository(session)
        await user_repo.get_or_create(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )
        break
    
    welcome_text = (
        "🤖 <b>Welcome to Crafted Escrow!</b>\n\n"
        "I'm your secure escrow bot for safe transactions.\n\n"
        "🔹 <b>How it works:</b>\n"
        "• Create a deal with buyer and seller\n"
        "• Both parties agree to terms\n"
        "• Escrower verifies payment\n"
        "• Deal completes or refunds as needed\n\n"
        "Use the buttons below to get started!"
    )
    
    await message.reply(
        welcome_text,
        reply_markup=get_main_menu_keyboard(is_staff)
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "📖 <b>Crafted Escrow Help</b>\n\n"
        "🔹 <b>Creating a Deal</b>\n"
        "Click 'Create Deal' and fill out the form.\n\n"
        "🔹 <b>Agreeing to Terms</b>\n"
        "Both parties must agree before payment.\n\n"
        "🔹 <b>Payment Verification</b>\n"
        "Only authorized escrowers can verify payments.\n\n"
        "🔹 <b>Commands</b>\n"
        "/add - Confirm payment received\n"
        "/done - Complete a deal\n"
        "/refund - Process a refund\n\n"
        "🔹 <b>Disputes</b>\n"
        "Use the dispute button on active deals.\n\n"
        "🔹 <b>Vouches</b>\n"
        "After completion, you'll be asked to vouch.\n\n"
        "For more help, contact staff."
    )
    
    await message.reply(help_text)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, is_staff: bool):
    """Return to main menu"""
    await callback.message.edit_text(
        "🏠 <b>Main Menu</b>\n\n"
        "Choose an option below:",
        reply_markup=get_main_menu_keyboard(is_staff)
    )
    await callback.answer()

@router.callback_query(F.data == "my_deals")
async def my_deals(callback: CallbackQuery, db_user):
    """Show user's deals"""
    async for session in get_session():
        deal_repo = DealRepository(session)
        deals = await deal_repo.get_deals_by_user(db_user.id)
        break
    
    if not deals:
        await callback.message.edit_text(
            "📁 <b>My Deals</b>\n\n"
            "You haven't participated in any deals yet.",
            reply_markup=get_deal_status_keyboard()
        )
        await callback.answer()
        return
    
    text = "📁 <b>My Deals</b>\n\n"
    
    # Show summary
    deal_stats = {
        'total': len(deals),
        'active': 0,
        'completed': 0,
        'refunded': 0,
        'disputed': 0,
        'cancelled': 0
    }
    
    for deal in deals:
        status = deal.status.value
        if status == 'ACTIVE':
            deal_stats['active'] += 1
        elif status == 'COMPLETED':
            deal_stats['completed'] += 1
        elif status == 'REFUNDED':
            deal_stats['refunded'] += 1
        elif status == 'DISPUTED':
            deal_stats['disputed'] += 1
        elif status == 'CANCELLED':
            deal_stats['cancelled'] += 1
    
    text += f"Total Deals: {deal_stats['total']}\n"
    text += f"🟢 Active: {deal_stats['active']}\n"
    text += f"✅ Completed: {deal_stats['completed']}\n"
    text += f"↩️ Refunded: {deal_stats['refunded']}\n"
    text += f"⚠️ Disputed: {deal_stats['disputed']}\n"
    text += f"❌ Cancelled: {deal_stats['cancelled']}\n\n"
    
    # Show recent deals
    text += "Recent Deals:\n"
    for deal in deals[:5]:
        text += f"• {deal.deal_id} - {deal.status.value} - {deal.item[:30]}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_deal_status_keyboard()
    )
    await callback.answer()
