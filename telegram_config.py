# Telegram Bot Configuration
# Copy this file to telegram_config.py and fill in your values

# Bot Configuration
BOT_TOKEN = "8132299847:AAGMblYkbshXrMN2iU9ahGpWkEaH2sWtAZY"  # Get from @BotFather on Telegram
USE_MONGODB = True  # Set to True if using MongoDB instead of SQLite

# Admin Configuration
ADMIN_USER_IDS = [
    # Add admin Telegram user IDs here
    # Get your ID from @userinfobot on Telegram
    # Example: 123456789, 987654321
    7447817163
]

# Database Configuration
DATABASE_PATH = "data/database/attendance.db"  # SQLite database path
MONGODB_URI = "mongodb://localhost:27017/"     # MongoDB URI if using MongoDB
MONGODB_DB_NAME = "attendance_system"          # MongoDB database name

# Face Recognition Configuration
FACE_CONFIDENCE_THRESHOLD = 0.7   # Lower threshold for more lenient detection
MIN_FACE_SIZE = (80, 80)          # Smaller minimum face size
MAX_FACE_SIZE = (800, 800)        # Maximum face size
FACE_DETECTION_SCALE_FACTOR = 1.1 # Scale factor for face detection
FACE_DETECTION_MIN_NEIGHBORS = 3  # Minimum neighbors for face detection

# Photo Processing Configuration
MAX_PHOTO_SIZE_MB = 5              # Maximum photo size in MB
SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".bmp"]
PHOTO_STORAGE_PATH = "data/registration_photos/"  # Path to store registration photos

# Registration Settings
AUTO_APPROVE = False               # Set to True to auto-approve registrations
REQUIRE_ADMIN_APPROVAL = True      # Require admin approval for registrations
ALLOW_REGISTRATION_UPDATES = False # Allow users to update their registration

# Notification Settings
NOTIFY_ADMINS_NEW_REGISTRATION = True
NOTIFY_USER_ON_APPROVAL = True
NOTIFY_USER_ON_REJECTION = True

# Bot Messages (Customize as needed)
WELCOME_MESSAGE = """
🏢 **Employee Self-Registration System**

Hello {user_name}! 👋

This bot allows you to register for the face recognition attendance system.

Ready to start? Use /register to begin!
"""

REGISTRATION_COMPLETE_MESSAGE = """
🎉 **Registration Complete!**

Your registration has been submitted for admin approval.
You'll be notified once it's processed.
"""

APPROVAL_MESSAGE = """
🎉 **Registration Approved!**

Your registration has been approved.
You can now use face recognition at the attendance kiosk!
"""