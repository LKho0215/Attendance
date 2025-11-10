MONGODB_CONFIG = {
    # Primary MongoDB connection string
    "connection_string": "mongodb://admin:admin@192.168.8.41:27016/attendance_system?authSource=admin",  # Production DB
    # "connection_string": "mongodb://admin:admin@192.168.8.41:27017/attendance_system?authSource=admin",  # Staging DB
    # "connection_string": "mongodb://localhost:27017/",  # Local DB
    
    # Database name
    "database_name": "attendance_system",
    
    # Connection timeout in milliseconds
    "timeout": 5000,
}

# Application Settings
APP_CONFIG = {
    "app_name": "Attendance Kiosk System",
    "version": "2.0.0",
    "debug": False
}
