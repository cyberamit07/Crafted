from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_panel_keyboard(is_owner: bool = False) -> InlineKeyboardMarkup:
    """Get admin panel keyboard"""
    buttons = [
        [InlineKeyboardButton(text="🛡 Escrowers", callback_data="manage_escrowers")],
        [InlineKeyboardButton(text="🔧 Admins", callback_data="manage_admins")],
        [InlineKeyboardButton(text="👥 Users", callback_data="manage_users")],
        [InlineKeyboardButton(text="🤝 Deals", callback_data="manage_deals")],
        [InlineKeyboardButton(text="📊 Statistics", callback_data="global_stats")],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton(text="📝 Logs", callback_data="view_logs")]
    ]
    
    if is_owner:
        buttons.insert(0, [InlineKeyboardButton(text="👑 Owner Panel", callback_data="owner_panel")])
    
    buttons.append([InlineKeyboardButton(text="◀️ Back", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
