# MongoDB Configuration for Attendance System
# Update the connection string below with your MongoDB Atlas connection string

# MongoDB Connection Configuration
MONGODB_CONFIG = {
    # Primary connection - Automatically detects the best available connection
    # Update this based on your deployment scenario:
    
    # SCENARIO 1: Development/Local Testing (Current)
    "connection_string": "mongodb://localhost:27017/",
    
    # SCENARIO 2: Company Server Room (Update when deploying)
    # "connection_string": "mongodb://[server-ip]:27017/",
    # Example: "connection_string": "mongodb://192.168.1.100:27017/",
    
    # SCENARIO 3: Company MongoDB Server with Authentication
    # "connection_string": "mongodb://username:password@server-ip:27017/attendance_system?authSource=admin",
    
    # SCENARIO 4: MongoDB Atlas Cloud (when SSL issues resolved)
    # "connection_string": "mongodb+srv://admin:admin@cluster0.r9ddy.mongodb.net/attendance_system?retryWrites=true&w=majority",
    
    # Fallback connections (tried in order if primary fails)
    "fallback_connections": [
        "mongodb://localhost:27017/",  # Local MongoDB
        "mongodb://127.0.0.1:27017/",  # Local MongoDB (IP)
        # Add company server IPs here when deploying:
        # "mongodb://192.168.1.100:27017/",  # Company server
        # "mongodb://company-db-server:27017/",  # Company server by hostname
    ],
    
    # Atlas connection (for cloud backup/sync)
    "atlas_connection": "mongodb+srv://admin:admin@cluster0.r9ddy.mongodb.net/attendance_system?retryWrites=true&w=majority",
    
    # Database name
    "database_name": "attendance_system",
    
    # Connection timeout (seconds)
    "timeout": 5000,
}

# Application Settings
APP_CONFIG = {
    "app_name": "Attendance Kiosk System",
    "version": "2.0.0",
    "debug": False
}

# Instructions for setup:
# 1. Go to MongoDB Atlas (cloud.mongodb.com)
# 2. Create a cluster if you haven't already
# 3. Click "Connect" -> "Connect your application"
# 4. Copy the connection string
# 5. Replace the connection_string above with your actual connection string
# 6. Replace <password> with your database user password
# 7. Replace <username> with your database username
