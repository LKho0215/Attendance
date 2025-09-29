#!/usr/bin/env python3
"""
Telegram Registration Bot Launcher
Simplified launcher with configuration management
"""

import os
import sys
import logging
from typing import List

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import telegram
        print("✅ python-telegram-bot installed")
        return True
    except ImportError:
        print("❌ python-telegram-bot not installed")
        print("📦 Install with: pip install python-telegram-bot>=20.0")
        return False

def create_config_if_not_exists():
    """Create config file if it doesn't exist"""
    config_file = "telegram_config.py"
    template_file = "telegram_config_template.py"
    
    if not os.path.exists(config_file):
        if os.path.exists(template_file):
            print(f"📝 Creating {config_file} from template...")
            with open(template_file, 'r') as template:
                content = template.read()
            with open(config_file, 'w') as config:
                config.write(content)
            print(f"✅ Created {config_file}")
            print(f"🔧 Please edit {config_file} with your bot token and admin IDs")
            return False
        else:
            print(f"❌ {template_file} not found")
            return False
    return True

def load_config():
    """Load configuration from config file"""
    try:
        sys.path.append(os.path.dirname(__file__))
        import telegram_config as config
        
        # Validate required settings
        if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("❌ Please set BOT_TOKEN in telegram_config.py")
            print("🤖 Get a token from @BotFather on Telegram")
            return None
        
        if not config.ADMIN_USER_IDS:
            print("⚠️  Warning: No admin user IDs configured")
            print("👥 Add admin user IDs to ADMIN_USER_IDS in telegram_config.py")
        
        return config
    except ImportError:
        print("❌ telegram_config.py not found or has errors")
        return None

def main():
    """Main launcher function"""
    print("🤖 Telegram Registration Bot Launcher")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Create config if needed
    if not create_config_if_not_exists():
        return
    
    # Load configuration
    config = load_config()
    if not config:
        return
    
    # Import bot after dependencies are confirmed
    try:
        from telegram_registration_bot import TelegramRegistrationBot
    except ImportError as e:
        print(f"❌ Error importing bot: {e}")
        return
    
    # Create and configure bot
    try:
        print("🔧 Initializing bot...")
        bot = TelegramRegistrationBot(config.BOT_TOKEN, config.USE_MONGODB)
        
        # Add admin users
        admin_count = 0
        for admin_id in config.ADMIN_USER_IDS:
            if isinstance(admin_id, int):
                bot.add_admin(admin_id)
                admin_count += 1
            else:
                print(f"⚠️  Warning: Invalid admin ID: {admin_id} (must be integer)")
        
        print(f"👥 Added {admin_count} admin user(s)")
        
        if admin_count == 0:
            print("⚠️  Warning: Running without admin users")
            print("   Registrations will be submitted but cannot be approved")
        
        # Create necessary directories
        os.makedirs("data/registration_photos", exist_ok=True)
        print("📁 Created necessary directories")
        
        # Start the bot
        print("🚀 Starting Telegram Registration Bot...")
        print("📱 Bot is ready to receive registrations!")
        print("🛑 Press Ctrl+C to stop")
        print("-" * 50)
        
        bot.run()
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        logging.error(f"Bot startup error: {e}", exc_info=True)

if __name__ == "__main__":
    main()