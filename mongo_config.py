MONGODB_CONFIG = {
    
    "connection_string": "mongodb://admin:admin@192.168.8.41:27016/attendance_system?authSource=admin", #prod db
    # "connection_string": "mongodb://admin:admin@192.168.8.41:27017/attendance_system?authSource=admin", # stag db

    
    "fallback_connections": [
        "mongodb://admin:admin@192.168.8.41:27015/attendance_system?authSource=admin",
    ],
    
    "atlas_connection": "mongodb+srv://admin:admin@cluster0.r9ddy.mongodb.net/attendance_system?retryWrites=true&w=majority",
    
    "database_name": "attendance_system",
    
    "timeout": 5000,
}

# Application Settings
APP_CONFIG = {
    "app_name": "Attendance Kiosk System",
    "version": "2.0.0",
    "debug": False
}
