from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import format_deal_id

def get_deal_form_keyboard() -> InlineKeyboardMarkup:
    """Get deal form navigation keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_deal")]
    ])

def get_agreement_keyboard(deal_id: str) -> InlineKeyboardMarkup:
    """Get agreement keyboard for buyer/seller"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Agree", callback_data=f"agree_{deal_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_agreement_{deal_id}")
        ]
    ])

def get_dispute_keyboard(deal_id: str) -> InlineKeyboardMarkup:
    """Get dispute keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Dispute", callback_data=f"dispute_{deal_id}")]
    ])
