from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from database.database import get_session
from database.repositories import StatsRepository, DealRepository, UserRepository
from utils.helpers import format_stats, format_deal_id

router = Router()

@router.callback_query(F.data == "global_stats")
async def show_global_stats(callback: CallbackQuery):
    """Show global statistics"""
    async for session in get_session():
        stats_repo = StatsRepository(session)
        stats = await stats_repo.get_global_stats()
        break
    
    await callback.message.edit_text(
        format_stats(stats),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("deals_status_"))
async def show_deals_by_status(callback: CallbackQuery, db_user):
    """Show deals by status"""
    status = callback.data.split("_")[2]
    
    from database.models import DealStatus
    deal_status = getattr(DealStatus, status.upper(), None)
    
    if not deal_status:
        await callback.answer("Invalid status")
        return
    
    async for session in get_session():
        deal_repo = DealRepository(session)
        deals = await deal_repo.get_deals_by_user(db_user.id, deal_status)
        break
    
    if not deals:
        await callback.answer(f"No {status} deals found.")
        return
    
    text = f"📁 <b>{status} Deals</b>\n\n"
    for deal in deals[:10]:  # Show first 10
        text += f"• {format_deal_id(deal.deal_id)} - {deal.item[:30]}\n"
        text += f"  Amount: {deal.amount} {deal.payment_method.name}\n\n"
    
    if len(deals) > 10:
        text += f"\n<i>Showing 10 of {len(deals)} deals</i>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="my_deals")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
