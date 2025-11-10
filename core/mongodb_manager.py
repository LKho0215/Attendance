from pymongo import MongoClient
from datetime import datetime
import os
import numpy as np
from bson import ObjectId

class MongoDBManager:
    def get_attendance_by_date(self, nric, date):
        """Get all attendance records for a specific employee on a specific date (date: datetime.date)"""
        try:
            if not self.ensure_connection():
                print("[MONGODB ERROR] Cannot establish connection for get_attendance_by_date query")
                return []
            start_datetime = datetime.combine(date, datetime.min.time())
            end_datetime = datetime.combine(date, datetime.max.time())
            pipeline = [
                {"$match": {
                    "nric": nric,
                    "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
                }},
                {"$lookup": {
                    "from": "employees",
                    "localField": "nric",
                    "foreignField": "nric",
                    "as": "employee"
                }},
                {"$unwind": "$employee"},
                {"$sort": {"timestamp": 1}},
                {"$project": {
                    "id": {"$toString": "$_id"},
                    "nric": 1,
                    "name": "$employee.name",
                    "timestamp": {"$dateToString": {"date": "$timestamp", "format": "%Y-%m-%d %H:%M:%S"}},
                    "method": 1,
                    "status": 1,
                    "attendance_type": 1,
                    "late": {"$ifNull": ["$late", False]},
                    "overtime_hours": {"$ifNull": ["$overtime_hours", 0]},
                    "location_name": {"$ifNull": ["$location_name", ""]},
                    "address": {"$ifNull": ["$address", ""]}
                }}
            ]
            records = list(self.attendance.aggregate(pipeline))
            print(f"[MONGODB] Found {len(records)} attendance records for {nric} on {date}")
            return records
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get attendance by date: {e}")
            return []
    def __init__(self, connection_string=None, database_name=None):
        """
        Initialize MongoDB connection
        Args:
            connection_string: MongoDB connection string (if None, will use config)
            database_name: Name of the database to use (if None, will use config)
        """
        # Import config
        try:
            from mongo_config import MONGODB_CONFIG
            if connection_string is None:
                connection_string = MONGODB_CONFIG.get("connection_string")
            if database_name is None:
                database_name = MONGODB_CONFIG.get("database_name", "attendance_system")
        except ImportError:
            print("[MONGODB ERROR] mongo_config.py not found!")
            raise Exception("MongoDB configuration file (mongo_config.py) is required")
        
        # Validate connection string
        if not connection_string:
            print("[MONGODB ERROR] No connection string provided in mongo_config.py")
            raise Exception("MongoDB connection string is required in mongo_config.py")
        
        try:
            print(f"[MONGODB] Connecting to MongoDB: {database_name}...")
            
            # Connect to MongoDB with timeout
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[database_name]
            
            # Test connection
            self.client.admin.command('ping')
            
            # Determine connection type for logging
            if "localhost" in connection_string or "127.0.0.1" in connection_string:
                print(f"[MONGODB] ✓ Successfully connected to local MongoDB: {database_name}")
            elif "mongodb+srv:" in connection_string or "mongodb.net" in connection_string:
                print(f"[MONGODB] ✓ Successfully connected to MongoDB Atlas: {database_name}")
            else:
                print(f"[MONGODB] ✓ Successfully connected to MongoDB server: {database_name}")
            
            # Initialize collections and indexes
            self.init_collections()
            
        except Exception as e:
            print(f"[MONGODB ERROR] ✗ Failed to connect to MongoDB!")
            print(f"[MONGODB ERROR] Error: {e}")
            print(f"[MONGODB ERROR] Connection string: {connection_string[:20]}...")
            print(f"[MONGODB ERROR] Please check:")
            print(f"[MONGODB ERROR]   1. MongoDB server is running")
            print(f"[MONGODB ERROR]   2. Connection string in mongo_config.py is correct")
            print(f"[MONGODB ERROR]   3. Network/firewall allows MongoDB connection")
            raise Exception(f"MongoDB connection failed: {e}")
    
    def init_collections(self):
        """Initialize collections and create indexes for performance"""
        try:
            # Employees collection
            self.employees = self.db.employees
            self.employees.create_index("nric", unique=True)
            
            # Attendance collection
            self.attendance = self.db.attendance
            # Create indexes for better query performance
            self.attendance.create_index("nric")
            self.attendance.create_index("timestamp")
            self.attendance.create_index([("nric", 1), ("timestamp", -1)])
            
            print("[MONGODB] Collections and indexes initialized")
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to initialize collections: {e}")
    
    def get_current_timestamp(self):
        """Get current timestamp as datetime object"""
        return datetime.now()
    
    def get_employee(self, nric):
        """Get employee information by NRIC"""
        try:
            employee = self.employees.find_one({"nric": nric})
            
            if employee:
                return {
                    'nric': employee['nric'],  # Include nric in returned dictionary
                    'username': employee['username'],
                    'name': employee['name'],
                    'department': employee.get('department'),
                    'roles': employee.get('roles', []),
                    'face_vectors': employee.get('face_vectors', [])
                }
            return None
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get employee: {e}")
            return None
    
    def get_all_employees(self):
        """Get all employees from the database"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                return []
                
            employees = self.employees.find({}).sort("name", 1)
            return [
                {
                    'username': emp['username'],
                    'nric': emp['nric'],
                    'name': emp['name'],
                    'department': emp.get('department', ''),
                    'roles': emp.get('roles', []),
                    'face_vectors': emp.get('face_vectors', [])
                }
                for emp in employees
            ]
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get employees: {e}")
            return []
    
    def get_all_face_vectors(self):
        """Get all employees with face vectors (new vectorized method)"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                return []
                
            # Look for both new format (face_vectors - plural) and legacy format (face_vector - singular)
            employees = self.employees.find({
                "$or": [
                    {"face_vectors": {"$ne": None, "$exists": True}},
                    {"face_vector": {"$ne": None, "$exists": True}}
                ]
            })
            
            result = []
            for emp in employees:
                employee_data = {
                    'username': emp['username'],
                    'nric': emp['nric'],
                    'name': emp['name'],
                    'department': emp.get('department'),
                    'roles': emp.get('roles', []),

                }
                
                # Check for new format first (face_vectors - plural array)
                if 'face_vectors' in emp and emp['face_vectors']:
                    employee_data['face_vectors'] = emp['face_vectors']
                    print(f"[MONGODB] Loaded {len(emp['face_vectors'])} face vectors for {emp['name']} ({emp['username']})")
                # Fallback to legacy format (face_vector - singular)
                elif 'face_vector' in emp and emp['face_vector']:
                    employee_data['face_vector'] = emp['face_vector']
                    print(f"[MONGODB] Loaded legacy face vector for {emp['name']} ({emp['username']})")

                result.append(employee_data)
            
            return result
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get face vectors: {e}")
            return []
    
    def record_attendance(self, nric, method, status="in", attendance_type="check", timestamp=None, location_data=None, late=False, overtime_hours=0):
        """Record attendance for an employee with optional location data for CHECK OUT, late flag, and overtime hours"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                return None
                
            if timestamp is None:
                timestamp = datetime.now()
            
            attendance_doc = {
                "nric": nric,
                "timestamp": timestamp,
                "method": method,
                "status": status,
                "attendance_type": attendance_type,
                "late": late,
                "overtime_hours": overtime_hours
            }
            
            if attendance_type == "check" and status == "out" and location_data:
                attendance_doc.update({
                    "location_name": location_data.get("location_name", ""),
                    "address": location_data.get("address", "")
                })
                
                # Add checkout type if provided
                if location_data.get("type"):
                    attendance_doc["type"] = location_data.get("type")
                    print(f"[MONGODB] Recording CHECK OUT type: {location_data.get('type')}")
                
                print(f"[MONGODB] Recording CHECK OUT with location: {location_data.get('location_name', 'Unknown')} - {location_data.get('address', '')}")
            
            result = self.attendance.insert_one(attendance_doc)
            
            status_msg = f"{attendance_type} {status}"
            if late and attendance_type == "clock" and status == "in":
                status_msg = f"LATE {attendance_type} {status}"
            elif overtime_hours > 0 and attendance_type == "clock" and status == "out":
                status_msg = f"{attendance_type} {status} (OT {overtime_hours}h)"

            print(f"[MONGODB] Recorded {status_msg} for employee {nric}")
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to record attendance: {e}")
            return None
    
    def update_attendance_location(self, record_id, location_data):
        """Update an existing attendance record with location information"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                return False
            
            from bson import ObjectId
            
            update_data = {
                "location_name": location_data.get("location_name", ""),
                "address": location_data.get("address", "")
            }
            
            # Add checkout type (personal or work)
            if location_data.get("type"):
                update_data["type"] = location_data.get("type")
                print(f"[MONGODB] Recording checkout type: {location_data.get('type')}")
            
            # Add emergency information if present
            if location_data.get("emergency_clockout"):
                update_data["emergency_clockout"] = True
                update_data["emergency_reason"] = location_data.get("emergency_reason", "")
                print(f"[MONGODB] Recording EMERGENCY CLOCK-OUT: {location_data.get('emergency_reason', 'No reason provided')}")
            
            result = self.attendance.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": update_data}
            )
            
            if result.matched_count > 0:
                emergency_flag = " [EMERGENCY]" if location_data.get("emergency_clockout") else ""
                type_flag = f" [{location_data.get('type', 'work').upper()}]" if location_data.get("type") else ""
                print(f"[MONGODB] Updated attendance record {record_id} with location: {location_data.get('location_name', 'Unknown')}{type_flag}{emergency_flag}")
                return True
            else:
                print(f"[MONGODB] Attendance record {record_id} not found")
                return False
                
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to update attendance location: {e}")
            return False
    
    def get_attendance_today(self):
        try:
            if not self.ensure_connection():
                print("[MONGODB ERROR] Cannot establish connection for attendance query")
                return []
                
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": today_start, "$lte": today_end}
                    }
                },
                {
                    "$lookup": {
                        "from": "employees",
                        "localField": "nric",
                        "foreignField": "nric",
                        "as": "employee"
                    }
                },
                {
                    "$unwind": "$employee"
                },
                {
                    "$sort": {"timestamp": -1}
                },
                {
                    "$project": {
                        "id": {"$toString": "$_id"},
                        "username": "$employee.username",
                        "nric": "$employee.nric",
                        "name": "$employee.name",
                        "roles": "$employee.roles",
                        "timestamp": {"$dateToString": {"date": "$timestamp", "format": "%Y-%m-%d %H:%M:%S"}},
                        "method": 1,
                        "status": 1,
                        "attendance_type": 1,
                        "late": {"$ifNull": ["$late", False]},
                        "location_name": {"$ifNull": ["$location_name", ""]},
                        "address": {"$ifNull": ["$address", ""]}
                    }
                }
            ]
            
            records = list(self.attendance.aggregate(pipeline))
            print(f"[MONGODB] Found {len(records)} attendance records for today")
            return records
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get today's attendance: {e}")
            return []
    
    def get_attendance_by_date_range(self, start_date, end_date):
        """Get attendance records for a specific date range"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                print("[MONGODB ERROR] Cannot establish connection for date range query")
                return []
                
            # Parse date strings and create datetime objects
            if isinstance(start_date, str):
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                start_datetime = start_date
                
            if isinstance(end_date, str):
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                end_datetime = end_date
            
            # Aggregation pipeline to join with employees collection
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
                    }
                },
                {
                    "$lookup": {
                        "from": "employees",
                        "localField": "nric",
                        "foreignField": "nric",
                        "as": "employee"
                    }
                },
                {
                    "$unwind": "$employee"
                },
                {
                    "$sort": {"timestamp": 1}  # Sort by timestamp ascending for date range exports
                },
                {
                    "$project": {
                        "id": {"$toString": "$_id"},
                        "username": "$employee.username",
                        "nric": "$employee.nric",
                        "name": "$employee.name",
                        "timestamp": {"$dateToString": {"date": "$timestamp", "format": "%Y-%m-%d %H:%M:%S"}},
                        "method": 1,
                        "status": 1,
                        "attendance_type": 1,
                        "late": {"$ifNull": ["$late", False]},
                        "overtime_hours": {"$ifNull": ["$overtime_hours", 0]},
                        "location_name": {"$ifNull": ["$location_name", ""]},
                        "address": {"$ifNull": ["$address", ""]}
                    }
                }
            ]
            
            records = list(self.attendance.aggregate(pipeline))
            print(f"[MONGODB] Found {len(records)} attendance records for date range {start_date} to {end_date}")
            return records
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get attendance by date range: {e}")
            return []
    
    def get_attendance_history(self, days=30):
        """Get attendance history for specified number of days"""
        try:
            from datetime import timedelta
            
            # Calculate date range
            start_date = datetime.now() - timedelta(days=days)
            
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": start_date}
                    }
                },
                {
                    "$lookup": {
                        "from": "employees",
                        "localField": "nric",
                        "foreignField": "nric",
                        "as": "employee"
                    }
                },
                {
                    "$unwind": "$employee"
                },
                {
                    "$sort": {"timestamp": -1}
                },
                {
                    "$project": {
                        "username": "$employee.username",
                        "nric": "$employee.nric",
                        "name": "$employee.name",
                        "timestamp": {"$dateToString": {"date": "$timestamp", "format": "%Y-%m-%d %H:%M:%S"}},
                        "method": 1,
                        "status": 1,
                        "attendance_type": {"$ifNull": ["$attendance_type", "check"]},
                        "late": {"$ifNull": ["$late", False]},
                        "location_name": {"$ifNull": ["$location_name", ""]},
                        "address": {"$ifNull": ["$address", ""]}
                    }
                }
            ]
            
            return list(self.attendance.aggregate(pipeline))
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get attendance history: {e}")
            return []
    
    def check_connection(self):
        """Check if MongoDB connection is still alive"""
        try:
            # Ping the server with a short timeout
            self.client.admin.command('ping', maxTimeMS=1000)
            return True
        except Exception as e:
            print(f"[MONGODB] Connection check failed: {e}")
            return False
    
    def reconnect(self):
        """Reconnect to MongoDB if connection is lost"""
        try:
            print("[MONGODB] Attempting to reconnect...")
            # Import config again to get connection details
            from mongo_config import MONGODB_CONFIG
            connection_string = MONGODB_CONFIG.get("connection_string")
            database_name = MONGODB_CONFIG.get("database_name", "attendance_system")
            
            # Close existing connection
            if hasattr(self, 'client'):
                try:
                    self.client.close()
                except:
                    pass
            
            # Create new connection
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[database_name]
            
            # Test connection
            self.client.admin.command('ping')
            print("[MONGODB] Reconnection successful")
            
            # Re-initialize collections
            self.init_collections()
            return True
            
        except Exception as e:
            print(f"[MONGODB ERROR] Reconnection failed: {e}")
            return False
    
    def ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        if not self.check_connection():
            print("[MONGODB] Connection lost, attempting to reconnect...")
            return self.reconnect()
        return True

    def close_connection(self):
        """Close the MongoDB connection"""
        try:
            self.client.close()
            print("[MONGODB] Connection closed")
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to close connection: {e}")

    def get_admin_settings(self):
        """Get admin settings from database"""
        try:
            settings = self.db.admin_settings.find_one()
            if settings:
                # Remove MongoDB's _id field
                settings.pop('_id', None)
                return settings
            return None
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get admin settings: {e}")
            return None

    def save_admin_settings(self, settings):
        """Save admin settings to database"""
        try:
            # Update or insert settings (upsert)
            self.db.admin_settings.replace_one(
                {},  # Empty filter to match any document
                settings,
                upsert=True  # Create if doesn't exist
            )
            print("[MONGODB] Admin settings saved successfully")
            return True
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to save admin settings: {e}")
            return False
