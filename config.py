import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    OWNER_ID = int(os.getenv('OWNER_ID'))
    MAIN_GROUP_ID = int(os.getenv('MAIN_GROUP_ID'))
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
    VOUCH_CHANNEL_ID = int(os.getenv('VOUCH_CHANNEL_ID'))
    BOT_USERNAME = os.getenv('BOT_USERNAME', 'crafted_escrow_bot')
    ESCROW_FEE_PERCENT = float(os.getenv('ESCROW_FEE_PERCENT', 0))
    
    DATABASE_URL = 'sqlite+aiosqlite:///crafted_escrow.db'
    
    DEAL_ID_PREFIX = 'CE'
    DEAL_ID_DIGITS = 6
    
    TIMEZONE = 'Asia/Kolkata'
    
    RATE_LIMIT = {
        'broadcast': 30,  # messages per second
        'vouch_request': 5
    }

config = Config()
