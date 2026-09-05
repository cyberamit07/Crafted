import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any
import pytz
from config import config

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('crafted_escrow.log'),
            logging.StreamHandler()
        ]
    )
    
    # Reduce aiogram logging
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

def format_deal_id(deal_id: str) -> str:
    """Format deal ID with hashtag"""
    return f"#{deal_id}"

def format_amount(amount: float, method: str) -> str:
    """Format amount with currency symbol"""
    symbols = {
        'INR': '₹',
        'GRAM': '💎',
        'USDT': '₮',
        'STARS': '⭐'
    }
    symbol = symbols.get(method, '')
    return f"{symbol}{amount:,.2f}"

def format_timestamp(dt: datetime) -> str:
    """Format timestamp in IST"""
    if not dt:
        return 'N/A'
    
    # Convert to IST
    ist = pytz.timezone(config.TIMEZONE)
    dt_ist = dt.replace(tzinfo=pytz.UTC).astimezone(ist)
    
    return dt_ist.strftime('%d %b %Y %H:%M IST')

def get_username_display(user) -> str:
    """Get user display name"""
    if not user:
        return 'Unknown User'
    
    if user.username:
        return f"@{user.username}"
    
    name_parts = []
    if user.first_name:
        name_parts.append(user.first_name)
    if user.last_name:
        name_parts.append(user.last_name)
    
    if name_parts:
        return ' '.join(name_parts)
    
    return f"User {user.telegram_id}"

def validate_telegram_id(telegram_id: str) -> bool:
    """Validate Telegram ID format"""
    try:
        int(telegram_id)
        return True
    except ValueError:
        return False

def parse_deal_id(text: str) -> Optional[str]:
    """Extract deal ID from text"""
    pattern = r'#?CE-\d{6}'
    match = re.search(pattern, text)
    if match:
        return match.group(0).lstrip('#')
    return None

def safe_truncate(text: str, max_length: int = 100) -> str:
    """Truncate text safely"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'

async def is_owner(user_id: int) -> bool:
    """Check if user is owner"""
    return user_id == config.OWNER_ID

def format_stats(stats: Dict[str, Any]) -> str:
    """Format statistics for display"""
    lines = [
        "#Crafted_Escrow",
        "",
        "📊 Gʟᴏʙᴀʟ Eѕᴄʀᴏᴡ Sᴛᴀᴛs",
        "",
        f"🤝 Total Deals: {stats.get('total_deals', 0)}",
        f"✅ Completed Deals: {stats.get('completed_count', 0)}",
        f"↩️ Refunded Deals: {stats.get('refunded_count', 0)}",
        f"🟢 Active Deals: {stats.get('active_count', 0)}",
        f"⚠️ Disputed Deals: {stats.get('disputed_count', 0)}",
        "",
        "💰 Tᴏᴛᴀʟ Vᴏʟᴜᴍᴇ",
    ]
    
    for method in ['INR', 'GRAM', 'USDT', 'STARS']:
        volume = stats.get(f'{method.lower()}_volume', 0)
        if volume > 0:
            lines.append(f"{method}: {format_amount(volume, method)}")
    
    lines.extend([
        "",
        f"👥 Total Users: {stats.get('total_users', 0)}",
        f"🛡 Active Escrowers: {stats.get('active_escrowers', 0)}",
        f"⭐ Vouches: {stats.get('vouch_count', 0)}"
    ])
    
    return "\n".join(lines)
