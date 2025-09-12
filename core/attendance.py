from datetime import datetime, timedelta, time
from core.database import DatabaseManager

class AttendanceManager:
    def __init__(self, db_manager):
        self.db = db_manager
        
        # Shift configurations
        self.EARLY_SHIFT = {
            'clock_in_before': time(7, 45),  # Must arrive before 7:45 AM
            'clock_out_time': time(17, 0),   # Must leave by 5:00 PM
            'name': 'Early Shift (7:45 AM - 5:00 PM)'
        }
        
        self.REGULAR_SHIFT = {
            'clock_in_before': time(8, 0),   # Must arrive before 8:00 AM
            'clock_out_time': time(17, 15),  # Must leave by 5:15 PM
            'name': 'Regular Shift (8:00 AM - 5:15 PM)'
        }
        
        # Test time override for testing purposes
        self.test_time_override = None
    
    def get_current_time(self):
        """Get current time, or test override time"""
        if self.test_time_override:
            return self.test_time_override
        return datetime.now()
    
    def set_test_time(self, time_str):
        """Set test time override (format: 'HH:MM')"""
        try:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            today = datetime.now().date()
            self.test_time_override = datetime.combine(today, time_obj)
        except ValueError:
            print(f"Invalid time format: {time_str}. Use HH:MM format.")
    
    def clear_test_time(self):
        """Clear test time override"""
        self.test_time_override = None
    
    def determine_shift_and_type(self, employee_id, current_time=None):
        """Determine shift type and attendance action based on arrival time"""
        if current_time is None:
            current_time = self.get_current_time()
            
        current_time_only = current_time.time()
        
        # Get today's records for this employee
        today_records = self.get_employee_attendance_today(employee_id)
        
        # Check if employee has already clocked in today
        clock_in_record = None
        for record in today_records:
            if record.get('attendance_type') == 'clock' and record['status'] == 'in':
                clock_in_record = record
                break
        
        if clock_in_record:
            # Employee already clocked in, determine current shift
            clock_in_time = datetime.fromisoformat(clock_in_record['timestamp']).time()
            
            if clock_in_time < self.EARLY_SHIFT['clock_in_before']:
                assigned_shift = self.EARLY_SHIFT
            else:
                assigned_shift = self.REGULAR_SHIFT
            
            # Always allow clock out attempt - let clock_out_employee handle time validation
            return assigned_shift, 'clock', 'out'
        
        else:
            # First time today - determine shift based on current time
            if current_time_only < self.EARLY_SHIFT['clock_in_before']:
                return self.EARLY_SHIFT, 'clock', 'in'
            elif current_time_only < self.REGULAR_SHIFT['clock_in_before']:
                return self.REGULAR_SHIFT, 'clock', 'in'
            else:
                # Allow late clock in (after 8:00 AM) but mark as late
                return self.REGULAR_SHIFT, 'clock', 'in_late'
    
    def process_attendance(self, employee_id, method, attendance_mode, location_callback=None):
        """Process attendance based on mode (clock/check) and current time"""
        employee = self.db.get_employee(employee_id)
        if not employee:
            return False, f"Employee {employee_id} not found"
        
        if attendance_mode.upper() == 'CLOCK':
            # CLOCK mode: Handle shift start/end times with time restrictions
            current_time = self.get_current_time()
            shift, att_type, action = self.determine_shift_and_type(employee_id, current_time)
            
            if action == 'in':
                return self.clock_in_employee(employee_id, method, shift)
            elif action == 'in_late':
                return self.clock_in_employee(employee_id, method, shift, is_late=True)
            elif action == 'out':
                return self.clock_out_employee(employee_id, method, shift)
            else:
                return False, f"Clock mode not available - use CHECK mode during work hours"
        
        elif attendance_mode.upper() == 'CHECK':
            # CHECK mode: Simple toggle for office entry/exit without time restrictions
            result = self.toggle_check_attendance(employee_id, method, location_callback)
            # Handle both old and new return formats
            if len(result) == 3:
                return result[0], result[1]  # success, message (ignore record_id for now)
            else:
                return result
        
        return False, "Invalid attendance mode"
    
    def clock_in_employee(self, employee_id, method, shift, is_late=False):
        """Clock in employee for shift start"""
        employee = self.db.get_employee(employee_id)
        
        # Check if already clocked in today
        today_records = self.get_employee_attendance_today(employee_id)
        for record in today_records:
            if record.get('attendance_type') == 'clock' and record['status'] == 'in':
                return False, f"{employee['name']} is already clocked in for {shift['name']}"
        
        # Record clock-in with late flag
        current_time = self.get_current_time()
        record_id = self.db.record_attendance(employee_id, method, "in", "clock", current_time, late=is_late)
        
        # Return appropriate message
        if is_late:
            return True, f"{employee['name']} LATE clock in (after 8:00 AM)"
        else:
            return True, f"{employee['name']} clocked in for {shift['name']}"
    
    def clock_out_employee(self, employee_id, method, shift):
        """Clock out employee for shift end with time restrictions"""
        employee = self.db.get_employee(employee_id)
        
        # Check if clocked in today and get clock-in record
        today_records = self.get_employee_attendance_today(employee_id)
        clock_in_record = None
        for record in today_records:
            if record.get('attendance_type') == 'clock' and record['status'] == 'in':
                clock_in_record = record
                break
        
        if not clock_in_record:
            return False, f"{employee['name']} hasn't clocked in today"
        
        # Check if already clocked out
        for record in today_records:
            if record.get('attendance_type') == 'clock' and record['status'] == 'out':
                return False, f"{employee['name']} is already clocked out"
        
        # Check clock-out time restrictions based on clock-in time
        current_time = self.get_current_time()
        current_time_only = current_time.time()
        
        # Get clock-in time from the record
        from datetime import datetime
        clock_in_time = datetime.fromisoformat(clock_in_record['timestamp']).time()
        
        # Determine minimum clock-out time based on clock-in time
        if clock_in_time < time(8, 0):  # Clocked in before 8:00 AM
            min_clock_out_time = time(17, 0)  # 5:00 PM
            shift_name = "Early Shift"
        else:  # Clocked in at 8:00 AM or later (including late arrivals)
            min_clock_out_time = time(17, 15)  # 5:15 PM
            shift_name = "Regular Shift"
        
        # Check if current time is before minimum clock-out time
        if current_time_only < min_clock_out_time:
            min_time_str = min_clock_out_time.strftime("%I:%M %p")
            return False, f"Cannot clock out before {min_time_str} ({shift_name})"
        
        # Record clock-out
        record_id = self.db.record_attendance(employee_id, method, "out", "clock", current_time)
        return True, f"{employee['name']} clocked out from {shift_name}"
    
    def toggle_check_attendance(self, employee_id, method, location_callback=None):
        """Toggle check in/out for office entry/exit during work hours"""
        employee = self.db.get_employee(employee_id)
        today_records = self.get_employee_attendance_today(employee_id)
        
        # Find most recent CHECK record (ignore CLOCK records)
        last_check_record = None
        check_records = [r for r in today_records if r.get('attendance_type') == 'check']
        
        if check_records:
            # Sort by ID descending to get the most recent CHECK record (ID is auto-incrementing)
            check_records.sort(key=lambda x: x.get('id', 0), reverse=True)
            last_check_record = check_records[0]
            # Use the most recent CHECK record to determine toggle behavior
        
        current_time = self.get_current_time()
        
        if not last_check_record:
            # First check of the day - CHECK OUT (default assumption is employee is leaving office)
            record_id = self.db.record_attendance(employee_id, method, "out", "check", current_time)
            
            # If location callback is provided, trigger location selection
            if location_callback:
                location_callback(record_id, employee_id)
                
            return True, f"{employee['name']} checked out of office", record_id
        else:
            # Toggle based on last check status
            if last_check_record['status'] == 'in':
                # CHECK OUT - need location selection
                record_id = self.db.record_attendance(employee_id, method, "out", "check", current_time)
                
                # If location callback is provided, trigger location selection
                if location_callback:
                    location_callback(record_id, employee_id)
                
                return True, f"{employee['name']} checked out of office", record_id
            else:
                # CHECK IN
                record_id = self.db.record_attendance(employee_id, method, "in", "check", current_time)
                return True, f"{employee['name']} checked into office", record_id
    
    def check_in_employee(self, employee_id, method="manual"):
        """Check in an employee"""
        # Verify employee exists
        employee = self.db.get_employee(employee_id)
        if not employee:
            return False, f"Employee {employee_id} not found"
        
        # Check if already checked in today
        today_records = self.get_employee_attendance_today(employee_id)
        if today_records:
            last_record = today_records[0]  # Most recent record
            if last_record['status'] == 'in':
                return False, f"{employee['name']} is already checked in"
        
        # Record check-in
        record_id = self.db.record_attendance(employee_id, method, "in")
        return True, f"{employee['name']} checked in successfully"
    
    def check_out_employee(self, employee_id, method="manual"):
        """Check out an employee"""
        # Verify employee exists
        employee = self.db.get_employee(employee_id)
        if not employee:
            return False, f"Employee {employee_id} not found"
        
        # Check if checked in today
        today_records = self.get_employee_attendance_today(employee_id)
        if not today_records:
            return False, f"{employee['name']} hasn't checked in today"
        
        last_record = today_records[0]  # Most recent record
        if last_record['status'] == 'out':
            return False, f"{employee['name']} is already checked out"
        
        # Record check-out
        record_id = self.db.record_attendance(employee_id, method, "out")
        return True, f"{employee['name']} checked out successfully"
    
    def toggle_attendance(self, employee_id, method="manual"):
        """Toggle attendance (check in if out, check out if in)"""
        employee = self.db.get_employee(employee_id)
        if not employee:
            return False, f"Employee {employee_id} not found"
        
        today_records = self.get_employee_attendance_today(employee_id)
        
        if not today_records:
            # No records today, check in
            return self.check_in_employee(employee_id, method)
        else:
            last_record = today_records[0]
            if last_record['status'] == 'in':
                # Last status was in, check out
                return self.check_out_employee(employee_id, method)
            else:
                # Last status was out, check in
                return self.check_in_employee(employee_id, method)
    
    def get_employee_attendance_today(self, employee_id):
        """Get today's attendance records for a specific employee"""
        all_today = self.db.get_attendance_today()
        return [record for record in all_today if record['employee_id'] == employee_id]
    
    def get_attendance_summary_today(self):
        """Get summary of today's attendance"""
        attendance_records = self.db.get_attendance_today()
        
        # Group by employee
        employee_status = {}
        for record in attendance_records:
            emp_id = record['employee_id']
            if emp_id not in employee_status:
                employee_status[emp_id] = {
                    'name': record['name'],
                    'status': 'out',
                    'check_in_time': None,
                    'check_out_time': None,
                    'total_hours': 0
                }
            
            if record['status'] == 'in':
                employee_status[emp_id]['status'] = 'in'
                employee_status[emp_id]['check_in_time'] = record['timestamp']
            elif record['status'] == 'out':
                employee_status[emp_id]['status'] = 'out'
                employee_status[emp_id]['check_out_time'] = record['timestamp']
        
        # Calculate working hours
        for emp_id, data in employee_status.items():
            if data['check_in_time'] and data['check_out_time']:
                check_in = datetime.fromisoformat(data['check_in_time'])
                check_out = datetime.fromisoformat(data['check_out_time'])
                data['total_hours'] = (check_out - check_in).total_seconds() / 3600
        
        return employee_status
    
    def get_attendance_statistics(self, days=30):
        """Get attendance statistics for the past N days"""
        records = self.db.get_attendance_history(days)
        
        # Count attendance by day
        daily_attendance = {}
        for record in records:
            date = record['timestamp'].split(' ')[0]  # Extract date part
            if date not in daily_attendance:
                daily_attendance[date] = set()
            daily_attendance[date].add(record['employee_id'])
        
        # Convert sets to counts
        daily_counts = {date: len(employees) for date, employees in daily_attendance.items()}
        
        # Get total unique employees
        all_employees = self.db.get_all_employees()
        total_employees = len(all_employees)
        
        # Calculate average attendance
        avg_attendance = sum(daily_counts.values()) / len(daily_counts) if daily_counts else 0
        attendance_rate = (avg_attendance / total_employees * 100) if total_employees > 0 else 0
        
        return {
            'total_employees': total_employees,
            'average_daily_attendance': avg_attendance,
            'attendance_rate_percentage': attendance_rate,
            'daily_counts': daily_counts
        }
    
    def generate_attendance_report(self, start_date=None, end_date=None):
        """Generate a comprehensive attendance report"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # This would be expanded to filter by date range
        # For now, using the existing method
        records = self.db.get_attendance_history(30)
        
        # Group by employee
        employee_reports = {}
        for record in records:
            emp_id = record['employee_id']
            if emp_id not in employee_reports:
                employee_reports[emp_id] = {
                    'name': record['name'],
                    'total_days': 0,
                    'check_ins': 0,
                    'check_outs': 0,
                    'methods_used': set()
                }
            
            employee_reports[emp_id]['methods_used'].add(record['method'])
            if record['status'] == 'in':
                employee_reports[emp_id]['check_ins'] += 1
            else:
                employee_reports[emp_id]['check_outs'] += 1
        
        # Convert sets to lists for JSON serialization
        for emp_data in employee_reports.values():
            emp_data['methods_used'] = list(emp_data['methods_used'])
            emp_data['total_days'] = min(emp_data['check_ins'], emp_data['check_outs'])
        
        return employee_reports
