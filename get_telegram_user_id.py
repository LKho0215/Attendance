#!/usr/bin/env python3
"""
Get Telegram User ID Helper
Simple script to help you get your Telegram user ID for admin configuration
"""

import asyncio
import sys

async def get_user_id_bot():
    """Simple bot to get user IDs"""
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    except ImportError:
        print("❌ python-telegram-bot not installed")
        print("📦 Install with: pip install python-telegram-bot>=20.0")
        return
    
    TOKEN = input("Enter your bot token: ").strip()
    
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please provide a valid bot token from @BotFather")
        return
    
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        username = user.username or "No username"
        first_name = user.first_name or "No first name"
        
        message = f"""
🆔 **Your Telegram User Information:**

**User ID:** `{user_id}`
**Username:** @{username}
**First Name:** {first_name}

📋 **To add as admin:**
Add `{user_id}` to `ADMIN_USER_IDS` in `telegram_config.py`

Example:
```
ADMIN_USER_IDS = [
    {user_id},  # {first_name}
]
```
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        print(f"\n✅ User ID for {first_name} (@{username}): {user_id}")
    
    async def any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await start(update, context)
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, any_message))
    
    print("🤖 User ID Bot started!")
    print("📱 Send any message to the bot to get your user ID")
    print("🛑 Press Ctrl+C to stop")
    
    # Start bot
    await application.run_polling()

def manual_method():
    """Manual method to get user ID"""
    print("\n📱 Manual Method to Get Your User ID:")
    print("=" * 40)
    print("1. Open Telegram")
    print("2. Search for @userinfobot")
    print("3. Send any message to @userinfobot")
    print("4. It will reply with your user ID")
    print("5. Copy that number to telegram_config.py")

def main():
    """Main function"""
    print("🆔 Telegram User ID Helper")
    print("=" * 30)
    print()
    print("Choose a method to get your Telegram user ID:")
    print("1. Use a temporary bot (requires bot token)")
    print("2. Manual method using @userinfobot")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        try:
            asyncio.run(get_user_id_bot())
        except KeyboardInterrupt:
            print("\n👋 Bot stopped")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    elif choice == "2":
        manual_method()
    elif choice == "3":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()