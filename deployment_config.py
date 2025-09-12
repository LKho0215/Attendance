#!/usr/bin/env python3
"""
MongoDB Deployment Configuration Tool
Helps configure MongoDB connection for different deployment scenarios.
"""

import os
import shutil
from datetime import datetime

def backup_current_config():
    """Backup current configuration"""
    if os.path.exists("mongo_config.py"):
        backup_name = f"mongo_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        shutil.copy("mongo_config.py", backup_name)
        print(f"✅ Current configuration backed up as: {backup_name}")

def create_local_config():
    """Configure for local development"""
    config = '''# MongoDB Configuration for Attendance System - LOCAL DEVELOPMENT
# Current deployment: Local MongoDB on same machine

MONGODB_CONFIG = {
    # Primary connection - Local MongoDB
    "connection_string": "mongodb://localhost:27017/",
    
    # Fallback connections
    "fallback_connections": [
        "mongodb://localhost:27017/",
        "mongodb://127.0.0.1:27017/",
    ],
    
    # Atlas connection (for backup/sync)
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
    "debug": False,
    "deployment": "local"
}
'''
    return config

def create_server_config(server_ip, username=None, password=None):
    """Configure for company server deployment"""
    
    if username and password:
        auth_conn = f"mongodb://{username}:{password}@{server_ip}:27017/attendance_system?authSource=admin"
        no_auth_conn = f"mongodb://{server_ip}:27017/"
    else:
        auth_conn = f"mongodb://{server_ip}:27017/"
        no_auth_conn = f"mongodb://{server_ip}:27017/"
    
    config = f'''# MongoDB Configuration for Attendance System - COMPANY SERVER
# Current deployment: MongoDB server at {server_ip}

MONGODB_CONFIG = {{
    # Primary connection - Company MongoDB Server
    "connection_string": "{auth_conn}",
    
    # Fallback connections (tried in order)
    "fallback_connections": [
        "{auth_conn}",
        "{no_auth_conn}",
        "mongodb://localhost:27017/",  # Local fallback
        "mongodb://127.0.0.1:27017/",
    ],
    
    # Atlas connection (for backup/sync)
    "atlas_connection": "mongodb+srv://admin:admin@cluster0.r9ddy.mongodb.net/attendance_system?retryWrites=true&w=majority",
    
    # Database name
    "database_name": "attendance_system",
    
    # Connection timeout (seconds)
    "timeout": 5000,
}}

# Application Settings
APP_CONFIG = {{
    "app_name": "Attendance Kiosk System",
    "version": "2.0.0",
    "debug": False,
    "deployment": "server",
    "server_ip": "{server_ip}"
}}
'''
    return config

def create_atlas_config():
    """Configure for MongoDB Atlas (cloud)"""
    config = '''# MongoDB Configuration for Attendance System - ATLAS CLOUD
# Current deployment: MongoDB Atlas cloud database

MONGODB_CONFIG = {
    # Primary connection - MongoDB Atlas
    "connection_string": "mongodb+srv://admin:admin@cluster0.r9ddy.mongodb.net/attendance_system?retryWrites=true&w=majority",
    
    # Fallback connections
    "fallback_connections": [
        "mongodb://localhost:27017/",  # Local fallback
        "mongodb://127.0.0.1:27017/",
    ],
    
    # Atlas connection (same as primary)
    "atlas_connection": "mongodb+srv://admin:admin@cluster0.r9ddy.mongodb.net/attendance_system?retryWrites=true&w=majority",
    
    # Database name
    "database_name": "attendance_system",
    
    # Connection timeout (seconds)
    "timeout": 10000,  # Longer timeout for cloud
}

# Application Settings
APP_CONFIG = {
    "app_name": "Attendance Kiosk System",
    "version": "2.0.0",
    "debug": False,
    "deployment": "atlas"
}
'''
    return config

def test_connection(config_content):
    """Test the MongoDB connection with new configuration"""
    print("\n🧪 Testing MongoDB connection...")
    
    # Write temporary config file
    with open("temp_config.py", "w") as f:
        f.write(config_content)
    
    try:
        # Import and test
        import sys
        sys.path.insert(0, ".")
        import temp_config
        
        from pymongo import MongoClient
        
        config = temp_config.MONGODB_CONFIG
        connection_string = config["connection_string"]
        
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        client.close()
        
        print("✅ Connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists("temp_config.py"):
            os.remove("temp_config.py")
        if "temp_config" in sys.modules:
            del sys.modules["temp_config"]

def main():
    """Main configuration tool"""
    print("MONGODB DEPLOYMENT CONFIGURATION TOOL")
    print("=" * 50)
    
    # Backup current config
    backup_current_config()
    
    print("\nSelect deployment scenario:")
    print("1. Local Development (MongoDB on same machine)")
    print("2. Company Server (MongoDB on different server)")  
    print("3. MongoDB Atlas (Cloud database)")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    config_content = None
    
    if choice == "1":
        print("\n📱 Configuring for Local Development...")
        config_content = create_local_config()
        
    elif choice == "2":
        print("\n🏢 Configuring for Company Server...")
        server_ip = input("Enter MongoDB server IP address (e.g., 192.168.1.100): ").strip()
        
        if not server_ip:
            print("❌ Server IP is required!")
            return
            
        use_auth = input("Does the server require authentication? (y/n): ").strip().lower()
        
        if use_auth in ['y', 'yes']:
            username = input("Enter MongoDB username: ").strip()
            password = input("Enter MongoDB password: ").strip()
            config_content = create_server_config(server_ip, username, password)
        else:
            config_content = create_server_config(server_ip)
            
    elif choice == "3":
        print("\n☁️ Configuring for MongoDB Atlas...")
        config_content = create_atlas_config()
        
    elif choice == "4":
        print("👋 Exiting...")
        return
        
    else:
        print("❌ Invalid choice!")
        return
    
    if config_content:
        # Test the connection first
        if test_connection(config_content):
            # Save the configuration
            with open("mongo_config.py", "w") as f:
                f.write(config_content)
            print(f"\n✅ Configuration saved successfully!")
            print("🚀 Your application is now ready to use the new database configuration.")
        else:
            print("\n❌ Configuration NOT saved due to connection test failure.")
            print("💡 Please check your settings and try again.")

if __name__ == "__main__":
    main()
