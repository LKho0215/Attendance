import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="data/database/attendance.db"):
        self.db_path = db_path
        self.ensure_db_directory()
        self.init_database()
    
    def ensure_db_directory(self):
        """Ensure the database directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create employees table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    department TEXT,
                    face_image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create attendance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    method TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attendance_type TEXT DEFAULT 'check',
                    FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
                )
            ''')
            
            # Add attendance_type column if it doesn't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE attendance ADD COLUMN attendance_type TEXT DEFAULT "check"')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            conn.commit()
    
    def add_employee(self, employee_id, name, department=None, face_image_path=None):
        """Add a new employee to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO employees (employee_id, name, department, face_image_path)
                    VALUES (?, ?, ?, ?)
                ''', (employee_id, name, department, face_image_path))
                
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Employee ID already exists
    
    def get_employee(self, employee_id):
        """Get employee information by employee ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT employee_id, name, department, face_image_path
                FROM employees
                WHERE employee_id = ?
            ''', (employee_id,))
            
            result = cursor.fetchone()
            if result:
                employee_id, name, department, face_image_path = result
                return {
                    'employee_id': employee_id,
                    'name': name,
                    'department': department,
                    'face_image_path': face_image_path
                }
            return None
    
    def get_all_employees(self):
        """Get all employees from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT employee_id, name, department
                FROM employees
                ORDER BY name
            ''')
            
            return [{'employee_id': row[0], 'name': row[1], 'department': row[2]} 
                   for row in cursor.fetchall()]
    
    def get_all_face_images(self):
        """Get all employees with face images"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT employee_id, name, face_image_path
                FROM employees
                WHERE face_image_path IS NOT NULL
            ''')
            
            employees = []
            for row in cursor.fetchall():
                employee_id, name, face_image_path = row
                employees.append({
                    'employee_id': employee_id,
                    'name': name,
                    'face_image_path': face_image_path
                })
            return employees
    
    def update_employee_face(self, employee_id, face_image_path):
        """Update employee's face image path"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE employees
                SET face_image_path = ?
                WHERE employee_id = ?
            ''', (face_image_path, employee_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def record_attendance(self, employee_id, method, status="in", attendance_type="check", timestamp=None):
        """Record attendance for an employee"""
        from datetime import datetime
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Use provided timestamp or current time
            if timestamp is None:
                local_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                local_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO attendance (employee_id, timestamp, method, status, attendance_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (employee_id, local_timestamp, method, status, attendance_type))
            conn.commit()
            return cursor.lastrowid
    
    def get_attendance_today(self):
        """Get today's attendance records"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current date in the same format as stored timestamps
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Get today's attendance records with ID for proper sorting
            cursor.execute('''
                SELECT a.id, a.employee_id, e.name, a.timestamp, a.method, a.status, a.attendance_type
                FROM attendance a
                JOIN employees e ON a.employee_id = e.employee_id
                WHERE DATE(a.timestamp) = ?
                ORDER BY a.timestamp DESC
            ''', (current_date,))
            
            records = cursor.fetchall()
            
            return [{'id': row[0], 'employee_id': row[1], 'name': row[2], 'timestamp': row[3], 
                    'method': row[4], 'status': row[5], 'attendance_type': row[6]} for row in records]
    
    def get_attendance_history(self, days=30):
        """Get attendance history for specified number of days"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.employee_id, e.name, a.timestamp, a.method, a.status
                FROM attendance a
                JOIN employees e ON a.employee_id = e.employee_id
                WHERE a.timestamp >= datetime('now', '-{} days')
                ORDER BY a.timestamp DESC
            '''.format(days))
            
            return [{'employee_id': row[0], 'name': row[1], 'timestamp': row[2], 
                    'method': row[3], 'status': row[4]} for row in cursor.fetchall()]
    
    def delete_employee(self, employee_id):
        """Delete an employee and their attendance records"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete attendance records first
            cursor.execute('DELETE FROM attendance WHERE employee_id = ?', (employee_id,))
            
            # Delete employee
            cursor.execute('DELETE FROM employees WHERE employee_id = ?', (employee_id,))
            
            conn.commit()
            return cursor.rowcount > 0
