# Telegram Bot Self-Registration Setup Guide

## 📱 Overview
This Telegram bot allows employees to register themselves for the face recognition attendance system. Employees can:
- Provide their employee details
- Upload their photo for face recognition
- Get approval from administrators
- Receive notifications about their registration status

## 🚀 Quick Setup Guide

### Step 1: Install Dependencies
```bash
pip install python-telegram-bot>=20.0
```

### Step 2: Create Telegram Bot
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` to BotFather
3. Choose a name for your bot (e.g., "Company Attendance Registration Bot")
4. Choose a username (e.g., "company_attendance_bot")
5. Copy the bot token (looks like: `1234567890:ABCDEF...`)

### Step 3: Configure the Bot
1. Copy `telegram_config_template.py` to `telegram_config.py`
2. Edit `telegram_config.py` and set:
   - `BOT_TOKEN`: Your bot token from BotFather
   - `ADMIN_USER_IDS`: List of admin Telegram user IDs
   - `USE_MONGODB`: True/False based on your database choice

### Step 4: Get Admin User IDs
To get your Telegram user ID:
1. Send a message to `@userinfobot`
2. It will reply with your user ID number
3. Add this number to `ADMIN_USER_IDS` in config

### Step 5: Run the Bot
```bash
python telegram_registration_bot.py
```

## 📋 Features

### For Employees:
- **Self Registration**: Complete registration without visiting the kiosk
- **Photo Upload**: Easy photo capture via mobile phone
- **Status Tracking**: Check registration status anytime
- **Notifications**: Get notified when registration is approved/rejected

### For Administrators:
- **Review Registrations**: See all pending registrations
- **Photo Review**: View uploaded photos before approval
- **One-Click Approval**: Approve or reject with a single click
- **Batch Notifications**: Get notified of all new registrations

### For System:
- **Face Vector Extraction**: Automatic face feature extraction
- **Database Integration**: Seamless integration with existing attendance system
- **Duplicate Prevention**: Prevents duplicate employee IDs
- **Error Handling**: Robust error handling and user feedback

## 🎯 User Journey

### Employee Registration Flow:
1. **Start**: Employee sends `/start` to bot
2. **Employee ID**: Enter their employee ID
3. **Name**: Provide full name
4. **Role**: Select Staff or Security role
5. **Photo**: Upload clear face photo
6. **Approval**: Wait for admin approval
7. **Complete**: Start using face recognition

### Admin Approval Flow:
1. **Notification**: Receive new registration alert
2. **Review**: Check employee details and photo
3. **Decision**: Approve or reject registration
4. **Database**: Employee automatically added to system
5. **Notification**: Employee notified of decision

## 🔧 Configuration Options

### Database Settings:
- **SQLite**: Set `USE_MONGODB = False` (default)
- **MongoDB**: Set `USE_MONGODB = True` and configure MongoDB URI

### Security Settings:
- **Auto Approval**: Set `AUTO_APPROVE = True` for automatic approval
- **Admin Approval**: Set `REQUIRE_ADMIN_APPROVAL = True` for manual approval

### Photo Settings:
- **Size Limit**: Configure `MAX_PHOTO_SIZE_MB`
- **Formats**: Supported formats in `SUPPORTED_IMAGE_FORMATS`

## 🛡️ Security Features

### Input Validation:
- Employee ID format validation
- Name format validation  
- Photo quality checks
- Duplicate prevention

### Access Control:
- Admin-only approval functions
- User session management
- Secure photo handling

### Data Protection:
- Encrypted photo storage
- Secure face vector processing
- Audit trail logging

## 📊 Bot Commands

### User Commands:
- `/start` - Show welcome message and instructions
- `/register` - Start new registration process
- `/status` - Check current registration status
- `/help` - Show help information

### Admin Commands:
- All user commands plus:
- Inline buttons for approve/reject
- Registration review interface
- User management functions

## 🔍 Troubleshooting

### Common Issues:

**Bot doesn't respond:**
- Check bot token is correct
- Ensure bot is started with `python telegram_registration_bot.py`
- Check internet connection

**Photo processing fails:**
- Ensure photo shows clear face
- Check image is not too large (< 5MB)
- Try different lighting conditions

**Database errors:**
- Check database file permissions
- Ensure database path exists
- Verify database is not corrupted

**Admin functions not working:**
- Verify admin user ID is correct
- Check admin is added to `ADMIN_USER_IDS`
- Ensure admin user ID is integer, not string

## 📱 Usage Examples

### Employee Registration:
```
User: /register
Bot: Please enter your Employee ID:
User: EMP001
Bot: Please enter your full name:
User: John Smith
Bot: Please select your role: [Staff] [Security]
User: [Clicks Staff]
Bot: Please upload a clear photo of your face:
User: [Sends photo]
Bot: Registration complete! Waiting for approval.
```

### Admin Approval:
```
Bot → Admin: New registration from John Smith (EMP001)
                [Photo attached]
                [Approve] [Reject] [Details]
Admin: [Clicks Approve]
Bot → Admin: Registration approved!
Bot → User: Your registration has been approved!
```

## 🔄 Integration with Attendance System

The bot seamlessly integrates with your existing attendance system:

1. **Face Vector**: Extracted using the same DeepFace model
2. **Database**: Uses same database structure and tables
3. **Employee Data**: Compatible with existing employee records
4. **Role System**: Supports Staff/Security role differentiation

## 📈 Benefits

### For Company:
- **Reduced Queue Time**: No physical queue at registration kiosk
- **24/7 Registration**: Employees can register anytime
- **Admin Control**: Maintain approval control and oversight
- **Scalability**: Handle many registrations simultaneously

### For Employees:
- **Convenience**: Register from anywhere using phone
- **Speed**: Quick registration process
- **Transparency**: Clear status updates and notifications
- **Flexibility**: No need to visit office during work hours

### For IT Team:
- **Integration**: Works with existing attendance system
- **Maintenance**: Single bot handles all registrations
- **Monitoring**: Comprehensive logging and error tracking
- **Security**: Secure handling of biometric data

## 🚀 Getting Started

1. Follow the setup guide above
2. Test with a few employees first
3. Add all admin user IDs
4. Announce to employees with bot username
5. Monitor registrations and approvals

Ready to revolutionize your employee registration process! 🎉