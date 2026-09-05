from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from database.database import get_session
from database.repositories import (
    UserRepository, EscrowerRepository, AdminRepository,
    LogRepository, StatsRepository
)
from services.logging_service import LoggingService
from keyboards.admin import get_admin_panel_keyboard
from utils.helpers import is_owner, get_username_display, validate_telegram_id

router = Router()

@router.message(Command("global"))
async def cmd_global(message: Message, is_owner: bool, is_staff: bool):
    """Show global statistics"""
    if not (is_owner or is_staff):
        await message.reply("⚠️ You don't have permission to view this.")
        return
    
    async for session in get_session():
        stats_repo = StatsRepository(session)
        stats = await stats_repo.get_global_stats()
        break
    
    text = "📊 <b>Global Statistics</b>\n\n"
    text += f"👥 Total Users: {stats.get('total_users', 0)}\n"
    text += f"🛡 Active Escrowers: {stats.get('active_escrowers', 0)}\n"
    text += f"🔧 Admins: {stats.get('admin_count', 0)}\n\n"
    text += "📈 <b>Deal Statistics</b>\n"
    text += f"🤝 Total Deals: {stats.get('total_deals', 0)}\n"
    text += f"🟢 Active: {stats.get('active_count', 0)}\n"
    text += f"✅ Completed: {stats.get('completed_count', 0)}\n"
    text += f"↩️ Refunded: {stats.get('refunded_count', 0)}\n"
    text += f"⚠️ Disputed: {stats.get('disputed_count', 0)}\n"
    text += f"❌ Cancelled: {stats.get('cancelled_count', 0)}\n\n"
    text += "💰 <b>Volume</b>\n"
    text += f"INR: ₹{stats.get('inr_volume', 0):,.2f}\n"
    text += f"GRAM: 💎{stats.get('gram_volume', 0):,.2f}\n"
    text += f"USDT: ₮{stats.get('usdt_volume', 0):,.2f}\n"
    text += f"STARS: ⭐{stats.get('stars_volume', 0):,.2f}\n"
    
    await message.reply(text)

@router.message(Command("addescrower"))
async def cmd_add_escrower(message: Message, is_owner: bool):
    """Add an escrower (Owner only)"""
    if not is_owner:
        await message.reply("⚠️ Only the Owner can add escrowers.")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.reply(
            "Usage: /addescrower <Telegram_ID>\n\n"
            "Example: /addescrower 123456789"
        )
        return
    
    telegram_id = args[1].strip()
    if not validate_telegram_id(telegram_id):
        await message.reply("⚠️ Invalid Telegram ID. Please provide a numeric ID.")
        return
    
    user_id = int(telegram_id)
    
    async for session in get_session():
        # Check if user exists
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        
        if not user:
            await message.reply(
                "⚠️ User not found. They need to start the bot first.\n"
                "Ask them to send /start to the bot."
            )
            return
        
        # Check if already an escrower
        escrower_repo = EscrowerRepository(session)
        if await escrower_repo.is_escrower(user_id):
            await message.reply("⚠️ This user is already an escrower.")
            return
        
        # Add as escrower
        success = await escrower_repo.add_escrower(user_id, message.from_user.id)
        
        if success:
            # Log
            log_repo = LogRepository(session)
            await log_repo.add_log(
                'ESCROWER_ADDED',
                user_id=user_id,
                username=user.username,
                details=f"Added by {get_username_display(message.from_user)}"
            )
            
            await session.commit()
            
            await message.reply(
                f"✅ <b>Escrower Added!</b>\n\n"
                f"User: {get_username_display(user)}\n"
                f"ID: {user_id}\n\n"
                "They now have escrower permissions."
            )
            
            # Notify the user
            try:
                await message.bot.send_message(
                    user_id,
                    "🎉 <b>You've been added as an Escrower!</b>\n\n"
                    "You can now verify payments, complete deals, and process refunds."
                )
            except:
                pass
        else:
            await message.reply("❌ Failed to add escrower. Please try again.")
        
        break

@router.message(Command("removeescrower"))
async def cmd_remove_escrower(message: Message, is_owner: bool):
    """Remove an escrower (Owner only)"""
    if not is_owner:
        await message.reply("⚠️ Only the Owner can remove escrowers.")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.reply(
            "Usage: /removeescrower <Telegram_ID>\n\n"
            "Example: /removeescrower 123456789"
        )
        return
    
    telegram_id = args[1].strip()
    if not validate_telegram_id(telegram_id):
        await message.reply("⚠️ Invalid Telegram ID.")
        return
    
    user_id = int(telegram_id)
    
    async for session in get_session():
        escrower_repo = EscrowerRepository(session)
        
        if not await escrower_repo.is_escrower(user_id):
            await message.reply("⚠️ This user is not an escrower.")
            return
        
        success = await escrower_repo.remove_escrower(user_id)
        
        if success:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(user_id)
            
            log_repo = LogRepository(session)
            await log_repo.add_log(
                'ESCROWER_REMOVED',
                user_id=user_id,
                username=user.username if user else None,
                details=f"Removed by {get_username_display(message.from_user)}"
            )
            
            await session.commit()
            
            await message.reply(
                f"✅ <b>Escrower Removed!</b>\n\n"
                f"User ID: {user_id}\n\n"
                "They no longer have escrower permissions."
            )
            
            try:
                await message.bot.send_message(
                    user_id,
                    "❌ <b>You've been removed as an Escrower.</b>\n\n"
                    "You no longer have escrower permissions."
                )
            except:
                pass
        else:
            await message.reply("❌ Failed to remove escrower.")
        
        break

@router.message(Command("listescrowers"))
async def cmd_list_escrowers(message: Message, is_staff: bool):
    """List all escrowers"""
    if not is_staff:
        await message.reply("⚠️ You don't have permission to view this.")
        return
    
    async for session in get_session():
        escrower_repo = EscrowerRepository(session)
        escrowers = await escrower_repo.get_all_escrowers()
        break
    
    if not escrowers:
        await message.reply("📋 No active escrowers found.")
        return
    
    text = "🛡 <b>Active Escrowers</b>\n\n"
    for i, escrower in enumerate(escrowers, 1):
        user = escrower.user
        text += f"{i}. {get_username_display(user)}\n"
        text += f"   ID: {user.telegram_id}\n"
        text += f"   Added: {escrower.added_at.strftime('%d %b %Y')}\n\n"
    
    await message.reply(text)

@router.message(Command("addadmin"))
async def cmd_add_admin(message: Message, is_owner: bool):
    """Add an admin (Owner only)"""
    if not is_owner:
        await message.reply("⚠️ Only the Owner can add admins.")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.reply(
            "Usage: /addadmin <Telegram_ID>\n\n"
            "Example: /addadmin 123456789"
        )
        return
    
    telegram_id = args[1].strip()
    if not validate_telegram_id(telegram_id):
        await message.reply("⚠️ Invalid Telegram ID.")
        return
    
    user_id = int(telegram_id)
    
    async for session in get_session():
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        
        if not user:
            await message.reply("⚠️ User not found.")
            return
        
        admin_repo = AdminRepository(session)
        if await admin_repo.is_admin(user_id):
            await message.reply("⚠️ This user is already an admin.")
            return
        
        success = await admin_repo.add_admin(user_id, message.from_user.id)
        
        if success:
            log_repo = LogRepository(session)
            await log_repo.add_log(
                'ADMIN_ADDED',
                user_id=user_id,
                username=user.username,
                details=f"Added by {get_username_display(message.from_user)}"
            )
            
            await session.commit()
            
            await message.reply(
                f"✅ <b>Admin Added!</b>\n\n"
                f"User: {get_username_display(user)}\n"
                f"ID: {user_id}"
            )
        else:
            await message.reply("❌ Failed to add admin.")
        
        break

@router.message(Command("removeadmin"))
async def cmd_remove_admin(message: Message, is_owner: bool):
    """Remove an admin (Owner only)"""
    if not is_owner:
        await message.reply("⚠️ Only the Owner can remove admins.")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.reply(
            "Usage: /removeadmin <Telegram_ID>\n\n"
            "Example: /removeadmin 123456789"
        )
        return
    
    telegram_id = args[1].strip()
    if not validate_telegram_id(telegram_id):
        await message.reply("⚠️ Invalid Telegram ID.")
        return
    
    user_id = int(telegram_id)
    
    async for session in get_session():
        admin_repo = AdminRepository(session)
        
        if not await admin_repo.is_admin(user_id):
            await message.reply("⚠️ This user is not an admin.")
            return
        
        success = await admin_repo.remove_admin(user_id)
        
        if success:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(user_id)
            
            log_repo = LogRepository(session)
            await log_repo.add_log(
                'ADMIN_REMOVED',
                user_id=user_id,
                username=user.username if user else None,
                details=f"Removed by {get_username_display(message.from_user)}"
            )
            
            await session.commit()
            
            await message.reply(
                f"✅ <b>Admin Removed!</b>\n\n"
                f"User ID: {user_id}"
            )
        else:
            await message.reply("❌ Failed to remove admin.")
        
        break

@router.message(Command("listadmins"))
async def cmd_list_admins(message: Message, is_staff: bool):
    """List all admins"""
    if not is_staff:
        await message.reply("⚠️ You don't have permission to view this.")
        return
    
    async for session in get_session():
        admin_repo = AdminRepository(session)
        admins = await admin_repo.get_all_admins()
        break
    
    if not admins:
        await message.reply("📋 No active admins found.")
        return
    
    text = "🔧 <b>Active Admins</b>\n\n"
    for i, admin in enumerate(admins, 1):
        user = admin.user
        text += f"{i}. {get_username_display(user)}\n"
        text += f"   ID: {user.telegram_id}\n\n"
    
    await message.reply(text)

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, is_owner: bool):
    """Broadcast message to all users (Owner only)"""
    if not is_owner:
        await message.reply("⚠️ Only the Owner can use this command.")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.reply(
            "Usage: /broadcast <message>\n\n"
            "Example: /broadcast Hello everyone!"
        )
        return
    
    broadcast_text = args[1].strip()
    
    # Confirm broadcast
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_broadcast"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_broadcast")
        ]
    ])
    
    await message.reply(
        f"📢 <b>Broadcast Preview</b>\n\n"
        f"{broadcast_text}\n\n"
        f"<i>This will be sent to all registered users.</i>\n"
        f"<i>Rate limit: 30 messages/second</i>\n\n"
        f"⚠️ Confirm to proceed.",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Execute broadcast"""
    await callback.message.edit_text(
        "📢 <b>Broadcasting...</b>\n\n"
        "Please wait, this may take a while."
    )
    
    # Get broadcast text from previous message
    broadcast_text = callback.message.text.split("\n\n")[1]
    
    async for session in get_session():
        user_repo = UserRepository(session)
        users = await user_repo.get_all_users()
        break
    
    success_count = 0
    fail_count = 0
    
    for i, user in enumerate(users):
        try:
            # Rate limit: 30 messages/second
            if i > 0 and i % 30 == 0:
                import asyncio
                await asyncio.sleep(1)
            
            await callback.bot.send_message(
                user.telegram_id,
                f"📢 <b>Announcement</b>\n\n{broadcast_text}"
            )
            success_count += 1
        except:
            fail_count += 1
    
    await callback.message.edit_text(
        f"✅ <b>Broadcast Complete!</b>\n\n"
        f"✅ Sent: {success_count}\n"
        f"❌ Failed: {fail_count}"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery):
    """Cancel broadcast"""
    await callback.message.edit_text("❌ Broadcast cancelled.")
    await callback.answer()
