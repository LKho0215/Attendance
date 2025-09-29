@echo off
echo 🤖 Telegram Bot Setup Script
echo ==============================

echo.
echo 📦 Installing required packages...
pip install python-telegram-bot>=20.0
pip install asyncio-mqtt>=0.11.0

echo.
echo 📝 Setting up configuration...
if not exist telegram_config.py (
    copy telegram_config_template.py telegram_config.py
    echo ✅ Created telegram_config.py from template
    echo.
    echo ⚠️  IMPORTANT: Edit telegram_config.py with your settings:
    echo    - Set BOT_TOKEN (get from @BotFather)
    echo    - Add admin user IDs to ADMIN_USER_IDS
    echo.
) else (
    echo ✅ telegram_config.py already exists
)

echo 📁 Creating directories...
if not exist "data\registration_photos" mkdir "data\registration_photos"
echo ✅ Created registration photos directory

echo.
echo 🎉 Setup complete!
echo.
echo 📋 Next steps:
echo 1. Edit telegram_config.py with your bot token and admin IDs
echo 2. Run: python start_telegram_bot.py
echo.
echo 📱 To create a bot:
echo 1. Message @BotFather on Telegram
echo 2. Send /newbot
echo 3. Follow the instructions
echo 4. Copy the token to telegram_config.py
echo.
pause