MONGODB_CONFIG = {
    
    "connection_string": "mongodb+srv://admin:admin@cluster0.r9ddy.mongodb.net/attendance_system?retryWrites=true&w=majority",
    
    "fallback_connections": [
        "mongodb://localhost:27017/",  
        "mongodb://127.0.0.1:27017/",  
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
