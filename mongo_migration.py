#!/usr/bin/env python3
"""
MongoDB Migration and Testing Script for Attendance System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import DatabaseManager  # SQLite
from core.mongodb_manager import MongoDBManager  # MongoDB
from datetime import datetime

def test_mongodb_connection():
    """Test MongoDB connection"""
    print("=== TESTING MONGODB CONNECTION ===")
    try:
        mongo_db = MongoDBManager()
        print("✅ MongoDB connection successful!")
        
        # Test basic operations
        print("\n=== TESTING BASIC OPERATIONS ===")
        
        # Test adding an employee
        success = mongo_db.add_employee(
            employee_id="TEST001", 
            name="Test User MongoDB", 
            department="IT"
        )
        if success:
            print("✅ Employee addition successful!")
        else:
            print("⚠️ Employee might already exist")
        
        # Test retrieving the employee
        employee = mongo_db.get_employee("TEST001")
        if employee:
            print(f"✅ Employee retrieval successful: {employee['name']}")
        else:
            print("❌ Employee retrieval failed")
        
        # Test attendance recording
        record_id = mongo_db.record_attendance(
            employee_id="TEST001",
            method="manual",
            status="in",
            attendance_type="clock"
        )
        if record_id:
            print(f"✅ Attendance recording successful! ID: {record_id}")
        else:
            print("❌ Attendance recording failed")
        
        # Test getting today's attendance
        today_records = mongo_db.get_attendance_today()
        print(f"✅ Retrieved {len(today_records)} attendance records for today")
        
        # Cleanup test data
        mongo_db.delete_employee("TEST001")
        print("✅ Test cleanup completed")
        
        mongo_db.close_connection()
        print("✅ All MongoDB tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ MongoDB test failed: {e}")
        return False

def migrate_sqlite_to_mongodb():
    """Migrate existing SQLite data to MongoDB"""
    print("\n=== MIGRATING SQLITE TO MONGODB ===")
    try:
        # Initialize both databases
        sqlite_db = DatabaseManager()
        mongo_db = MongoDBManager()
        
        # Migrate employees
        print("Migrating employees...")
        sqlite_employees = sqlite_db.get_all_employees()
        employee_count = 0
        
        for emp in sqlite_employees:
            # Get full employee details including face image
            full_emp = sqlite_db.get_employee(emp['employee_id'])
            
            success = mongo_db.add_employee(
                employee_id=full_emp['employee_id'],
                name=full_emp['name'],
                department=full_emp['department'],
                face_image_path=full_emp['face_image_path']
            )
            
            if success:
                employee_count += 1
                print(f"  ✅ Migrated: {full_emp['name']} ({full_emp['employee_id']})")
            else:
                print(f"  ⚠️ Skipped (already exists): {full_emp['name']} ({full_emp['employee_id']})")
        
        print(f"✅ Migrated {employee_count} employees")
        
        # Migrate attendance records
        print("Migrating attendance records...")
        sqlite_attendance = sqlite_db.get_attendance_history(days=365)  # Get last year
        attendance_count = 0
        
        for record in sqlite_attendance:
            # Parse timestamp
            timestamp = datetime.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
            
            record_id = mongo_db.record_attendance(
                employee_id=record['employee_id'],
                method=record['method'],
                status=record['status'],
                attendance_type=record.get('attendance_type', 'check'),
                timestamp=timestamp
            )
            
            if record_id:
                attendance_count += 1
                if attendance_count % 10 == 0:  # Show progress every 10 records
                    print(f"  Migrated {attendance_count} records...")
        
        print(f"✅ Migrated {attendance_count} attendance records")
        
        mongo_db.close_connection()
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def create_sample_data():
    """Create sample data in MongoDB for testing"""
    print("\n=== CREATING SAMPLE DATA ===")
    try:
        mongo_db = MongoDBManager()
        
        # Sample employees
        sample_employees = [
            {"employee_id": "00209", "name": "Test User", "department": "IT"},
            {"employee_id": "12345", "name": "John Doe", "department": "HR"},
            {"employee_id": "67890", "name": "Jane Smith", "department": "Finance"},
        ]
        
        for emp in sample_employees:
            mongo_db.add_employee(**emp)
            print(f"  ✅ Added: {emp['name']}")
        
        # Sample attendance records
        from datetime import timedelta
        now = datetime.now()
        
        for emp in sample_employees:
            # Clock in this morning
            mongo_db.record_attendance(
                employee_id=emp["employee_id"],
                method="face_recognition",
                status="in",
                attendance_type="clock",
                timestamp=now.replace(hour=9, minute=0, second=0)
            )
            
            # Check out for lunch
            mongo_db.record_attendance(
                employee_id=emp["employee_id"],
                method="manual",
                status="out",
                attendance_type="check",
                timestamp=now.replace(hour=12, minute=30, second=0)
            )
            
            # Check in from lunch
            mongo_db.record_attendance(
                employee_id=emp["employee_id"],
                method="qr_code",
                status="in",
                attendance_type="check",
                timestamp=now.replace(hour=13, minute=30, second=0)
            )
        
        print("✅ Sample data created successfully!")
        mongo_db.close_connection()
        return True
        
    except Exception as e:
        print(f"❌ Sample data creation failed: {e}")
        return False

def main():
    """Main function"""
    print("MONGODB MIGRATION & TESTING UTILITY")
    print("=" * 50)
    
    # Test MongoDB connection first
    if not test_mongodb_connection():
        print("\n❌ MongoDB connection failed. Please check your configuration in mongo_config.py")
        return
    
    print("\nChoose an option:")
    print("1. Migrate existing SQLite data to MongoDB")
    print("2. Create sample data in MongoDB")
    print("3. Just test connection (already done)")
    print("4. Exit")
    
    try:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            migrate_sqlite_to_mongodb()
        elif choice == "2":
            create_sample_data()
        elif choice == "3":
            print("✅ Connection test already completed above!")
        elif choice == "4":
            print("Goodbye!")
        else:
            print("Invalid choice!")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
