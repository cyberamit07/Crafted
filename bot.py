import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.database import init_db
from handlers import (
    start, deal, staff, escrow, stats, vouch, dispute
)
from middlewares.permissions import PermissionsMiddleware
from utils.helpers import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Register middlewares
dp.message.middleware(PermissionsMiddleware())
dp.callback_query.middleware(PermissionsMiddleware())

# Register routers
dp.include_router(start.router)
dp.include_router(deal.router)
dp.include_router(staff.router)
dp.include_router(escrow.router)
dp.include_router(stats.router)
dp.include_router(vouch.router)
dp.include_router(dispute.router)

async def main():
    """Main bot entry point"""
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Set bot commands
        await bot.set_my_commands([
            ("start", "Start the bot"),
            ("help", "Get help"),
            ("global", "View global statistics"),
            ("addescrower", "Add escrower (Owner only)"),
            ("removeescrower", "Remove escrower (Owner only)"),
            ("listescrowers", "List all escrowers"),
            ("addadmin", "Add admin (Owner only)"),
            ("removeadmin", "Remove admin (Owner only)"),
            ("listadmins", "List all admins")
        ])
        
        logger.info("Bot started successfully")
        
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
