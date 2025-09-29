from pymongo import MongoClient
from datetime import datetime
import os
import numpy as np
from bson import ObjectId

class MongoDBManager:
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
            print("[MONGODB] No config found, using defaults")
            if connection_string is None:
                connection_string = "mongodb://localhost:27017/"
            if database_name is None:
                database_name = "attendance_system"
        
        try:
            # Try main connection string first
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=3000)
            self.db = self.client[database_name]
            
            # Test connection
            self.client.admin.command('ping')
            
            # Determine connection type for logging
            if "localhost" in connection_string or "127.0.0.1" in connection_string:
                print(f"[MONGODB] Successfully connected to local MongoDB: {database_name}")
            elif "mongodb+srv:" in connection_string or "mongodb.net" in connection_string:
                print(f"[MONGODB] Successfully connected to MongoDB Atlas: {database_name}")
            else:
                print(f"[MONGODB] Successfully connected to MongoDB server: {database_name}")
            
            # Initialize collections and indexes
            self.init_collections()
            
        except Exception as e:
            print(f"[MONGODB ERROR] Primary connection failed: {e}")
            
            # Try fallback connections in order
            try:
                from mongo_config import MONGODB_CONFIG
                fallback_connections = MONGODB_CONFIG.get("fallback_connections", [])
                
                for fallback_conn in fallback_connections:
                    if fallback_conn == connection_string:
                        continue  # Skip if same as primary
                        
                    try:
                        print(f"[MONGODB] Trying fallback: {fallback_conn}")
                        self.client = MongoClient(fallback_conn, serverSelectionTimeoutMS=3000)
                        self.db = self.client[database_name]
                        self.client.admin.command('ping')
                        
                        # Determine connection type for logging
                        if "localhost" in fallback_conn or "127.0.0.1" in fallback_conn:
                            print(f"[MONGODB] Connected to local MongoDB fallback: {database_name}")
                        else:
                            print(f"[MONGODB] Connected to server fallback: {database_name}")
                            
                        self.init_collections()
                        return  # Success, exit the retry loop
                        
                    except Exception as fallback_error:
                        print(f"[MONGODB] Fallback {fallback_conn} failed: {fallback_error}")
                        continue
                
                # If all fallbacks failed, try Atlas as last resort
                atlas_connection = MONGODB_CONFIG.get("atlas_connection")
                if atlas_connection and atlas_connection != connection_string:
                    print("[MONGODB] Trying Atlas as final fallback...")
                    self.client = MongoClient(atlas_connection, serverSelectionTimeoutMS=5000)
                    self.db = self.client[database_name]
                    self.client.admin.command('ping')
                    print(f"[MONGODB] Connected to Atlas fallback: {database_name}")
                    self.init_collections()
                else:
                    raise Exception("All connection methods failed")
                    
            except Exception as e2:
                print(f"[MONGODB ERROR] All connection attempts failed: {e2}")
                raise
    
    def init_collections(self):
        """Initialize collections and create indexes for performance"""
        try:
            # Employees collection
            self.employees = self.db.employees
            # Create unique index on employee_id
            self.employees.create_index("employee_id", unique=True)
            
            # Attendance collection
            self.attendance = self.db.attendance
            # Create indexes for better query performance
            self.attendance.create_index("employee_id")
            self.attendance.create_index("timestamp")
            self.attendance.create_index([("employee_id", 1), ("timestamp", -1)])
            
            # Location history collection
            self.location_history = self.db.location_history
            self.location_history.create_index("employee_id")
            self.location_history.create_index("timestamp")
            
            # Favorite locations collection
            self.favorite_locations = self.db.favorite_locations
            self.favorite_locations.create_index("employee_id")
            
            print("[MONGODB] Collections and indexes initialized")
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to initialize collections: {e}")
    
    def get_current_timestamp(self):
        """Get current timestamp as datetime object"""
        return datetime.now()
    
    def add_employee(self, employee_id, name, department=None, role="Staff", face_image_path=None):
        """Add a new employee to the database"""
        try:
            employee_doc = {
                "employee_id": employee_id,
                "name": name,
                "department": department,
                "role": role,
                "face_image_path": face_image_path,
                "created_at": datetime.now()
            }
            
            result = self.employees.insert_one(employee_doc)
            print(f"[MONGODB] Added employee: {name} ({employee_id}) - {role}")
            return True
            
        except Exception as e:
            if "duplicate key" in str(e).lower():
                print(f"[MONGODB] Employee ID {employee_id} already exists")
                return False
            print(f"[MONGODB ERROR] Failed to add employee: {e}")
            return False
    
    def get_employee(self, employee_id):
        """Get employee information by employee ID"""
        try:
            employee = self.employees.find_one({"employee_id": employee_id})
            
            if employee:
                return {
                    'employee_id': employee['employee_id'],
                    'name': employee['name'],
                    'department': employee.get('department'),
                    'role': employee.get('role', 'Staff'),
                    'face_image_path': employee.get('face_image_path')
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
                    'employee_id': emp['employee_id'],
                    'name': emp['name'],
                    'department': emp.get('department', ''),
                    'role': emp.get('role', 'Staff'),
                    'face_vector': emp.get('face_vector')  # Include face vector for DeepFace recognition
                }
                for emp in employees
            ]
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get employees: {e}")
            return []
    
    def get_all_face_images(self):
        """Get all employees with face images (legacy method for backward compatibility)"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                return []
                
            employees = self.employees.find({
                "face_image_path": {"$ne": None, "$ne": ""}
            })
            
            return [
                {
                    'employee_id': emp['employee_id'],
                    'name': emp['name'],
                    'face_image_path': emp['face_image_path']
                }
                for emp in employees
            ]
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get face images: {e}")
            return []
    
    def get_all_face_vectors(self):
        """Get all employees with face vectors (new vectorized method)"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                return []
                
            employees = self.employees.find({
                "face_vector": {"$ne": None, "$exists": True}
            })
            
            return [
                {
                    'employee_id': emp['employee_id'],
                    'name': emp['name'],
                    'department': emp.get('department'),
                    'role': emp.get('role', 'Staff'),
                    'face_vector': emp['face_vector']
                }
                for emp in employees
            ]
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to get face vectors: {e}")
            return []
    
    def update_employee_face_image(self, employee_id, face_image_path):
        """Update an employee's face image path (legacy method)"""
        try:
            result = self.employees.update_one(
                {"employee_id": employee_id},
                {"$set": {"face_image_path": face_image_path}}
            )
            
            if result.matched_count > 0:
                print(f"[MONGODB] Updated face image for employee {employee_id}")
                return True
            else:
                print(f"[MONGODB] Employee {employee_id} not found")
                return False
                
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to update face image: {e}")
            return False
    
    def update_employee_face_vector(self, employee_id, face_vector):
        """Update an employee's face vector (new vectorized method)"""
        try:
            # Ensure face_vector is a list for JSON serialization
            if isinstance(face_vector, np.ndarray):
                face_vector = face_vector.tolist()
            
            result = self.employees.update_one(
                {"employee_id": employee_id},
                {"$set": {"face_vector": face_vector, "face_vector_updated": self.get_current_timestamp()}}
            )
            
            if result.matched_count > 0:
                print(f"[MONGODB] Updated face vector for employee {employee_id}")
                return True
            else:
                print(f"[MONGODB] Employee {employee_id} not found")
                return False
                
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to update face vector: {e}")
            return False
    
    def add_employee_with_face_vector(self, employee_id, name, face_vector, department=None, role="Staff"):
        """Add a new employee with face vector"""
        try:
            # Ensure face_vector is a list for JSON serialization
            if isinstance(face_vector, np.ndarray):
                face_vector = face_vector.tolist()
                
            employee_data = {
                "employee_id": employee_id,
                "name": name,
                "department": department,
                "role": role,
                "face_vector": face_vector,
                "face_vector_created": self.get_current_timestamp(),
                "created_at": self.get_current_timestamp()
            }
            
            result = self.employees.insert_one(employee_data)
            if result.inserted_id:
                print(f"[MONGODB] Added employee {employee_id} ({role}) with face vector")
                return True
            return False
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to add employee with face vector: {e}")
            return False
    
    def has_face_vector(self, employee_id):
        """Check if an employee has a face vector stored"""
        try:
            employee = self.employees.find_one(
                {"employee_id": employee_id},
                {"face_vector": 1}
            )
            
            return employee and employee.get('face_vector') is not None
            
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to check face vector: {e}")
            return False
    
    def record_attendance(self, employee_id, method, status="in", attendance_type="check", timestamp=None, location_data=None, late=False):
        """Record attendance for an employee with optional location data for CHECK OUT and late flag"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                return None
                
            if timestamp is None:
                timestamp = datetime.now()
            
            attendance_doc = {
                "employee_id": employee_id,
                "timestamp": timestamp,
                "method": method,
                "status": status,
                "attendance_type": attendance_type,
                "late": late  # Add late flag
            }
            
            # Add location information for CHECK OUT records
            if attendance_type == "check" and status == "out" and location_data:
                attendance_doc.update({
                    "location_name": location_data.get("location_name", ""),
                    "address": location_data.get("address", "")
                })
                print(f"[MONGODB] Recording CHECK OUT with location: {location_data.get('location_name', 'Unknown')} - {location_data.get('address', '')}")
            
            result = self.attendance.insert_one(attendance_doc)
            
            # Update log message to indicate late status
            status_msg = f"{attendance_type} {status}"
            if late and attendance_type == "clock" and status == "in":
                status_msg = f"LATE {attendance_type} {status}"
            
            print(f"[MONGODB] Recorded {status_msg} for employee {employee_id}")
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
            
            result = self.attendance.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": update_data}
            )
            
            if result.matched_count > 0:
                print(f"[MONGODB] Updated attendance record {record_id} with location: {location_data.get('location_name', 'Unknown')}")
                return True
            else:
                print(f"[MONGODB] Attendance record {record_id} not found")
                return False
                
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to update attendance location: {e}")
            return False
    
    def get_attendance_today(self):
        """Get today's attendance records"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                print("[MONGODB ERROR] Cannot establish connection for attendance query")
                return []
                
            # Get start and end of today
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Aggregation pipeline to join with employees collection
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": today_start, "$lte": today_end}
                    }
                },
                {
                    "$lookup": {
                        "from": "employees",
                        "localField": "employee_id",
                        "foreignField": "employee_id",
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
                        "employee_id": 1,
                        "name": "$employee.name",
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
                        "localField": "employee_id",
                        "foreignField": "employee_id",
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
                        "employee_id": 1,
                        "name": "$employee.name",
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
                        "localField": "employee_id",
                        "foreignField": "employee_id",
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
                        "employee_id": 1,
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
    
    def delete_employee(self, employee_id):
        """Delete an employee and their attendance records"""
        try:
            # Delete attendance records first
            attendance_result = self.attendance.delete_many({"employee_id": employee_id})
            
            # Delete employee
            employee_result = self.employees.delete_one({"employee_id": employee_id})
            
            if employee_result.deleted_count > 0:
                print(f"[MONGODB] Deleted employee {employee_id} and {attendance_result.deleted_count} attendance records")
                return True
            else:
                print(f"[MONGODB] Employee {employee_id} not found")
                return False
                
        except Exception as e:
            print(f"[MONGODB ERROR] Failed to delete employee: {e}")
            return False
    
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
