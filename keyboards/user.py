from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard(is_staff: bool = False) -> InlineKeyboardMarkup:
    """Get main menu keyboard"""
    buttons = [
        [InlineKeyboardButton(text="🤝 Create Deal", callback_data="create_deal")],
        [InlineKeyboardButton(text="📊 Global Stats", callback_data="global_stats")],
        [InlineKeyboardButton(text="📁 My Deals", callback_data="my_deals")],
        [InlineKeyboardButton(text="ℹ️ Help", callback_data="help")]
    ]
    
    if is_staff:
        buttons.append([InlineKeyboardButton(text="👑 Staff Panel", callback_data="staff_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_deal_status_keyboard() -> InlineKeyboardMarkup:
    """Get deal status filter keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Active", callback_data="deals_status_active")],
        [InlineKeyboardButton(text="✅ Completed", callback_data="deals_status_completed")],
        [InlineKeyboardButton(text="↩️ Refunded", callback_data="deals_status_refunded")],
        [InlineKeyboardButton(text="⚠️ Disputed", callback_data="deals_status_disputed")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_main")]
    ])
