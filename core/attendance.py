from datetime import datetime, timedelta, time

class AttendanceManager:
    def __init__(self, db_manager):
        self.db = db_manager
        
        # Grace period for clock-in (15 minutes buffer)
        self.CLOCK_IN_GRACE_PERIOD_MINUTES = 15
        
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
        
        # Default minimum clock-out time (can be overridden by admin settings)
        self.min_clock_out_time = time(17, 0)  # 5:00 PM default
        
        # Test time override for testing purposes
        self.test_time_override = None
    
    def update_min_clock_out_time(self, time_str):
        """Update the minimum clock-out time from admin settings (legacy method)"""
        try:
            # Parse HH:MM format
            hour, minute = map(int, time_str.split(':'))
            self.min_clock_out_time = time(hour, minute)
            print(f"[ATTENDANCE] Updated minimum clock-out time to {self.min_clock_out_time.strftime('%I:%M %p')}")
        except Exception as e:
            print(f"[ATTENDANCE] Error updating min clock-out time: {e}")
            # Keep default if parsing fails
            self.min_clock_out_time = time(17, 0)
    
    def update_shift_settings(self, early_shift_min_clockout, regular_shift_min_clockout):
        """Update shift settings with separate times for early and regular shifts"""
        try:
            # Parse early shift time
            early_hour, early_minute = map(int, early_shift_min_clockout.split(':'))
            self.EARLY_SHIFT['clock_out_time'] = time(early_hour, early_minute)
            
            # Parse regular shift time
            regular_hour, regular_minute = map(int, regular_shift_min_clockout.split(':'))
            self.REGULAR_SHIFT['clock_out_time'] = time(regular_hour, regular_minute)
            
            # Update the legacy min_clock_out_time to regular shift for backward compatibility
            self.min_clock_out_time = self.REGULAR_SHIFT['clock_out_time']
            
            print(f"[ATTENDANCE] Updated shift settings:")
            print(f"  Early Shift: {self.EARLY_SHIFT['clock_out_time'].strftime('%I:%M %p')}")
            print(f"  Regular Shift: {self.REGULAR_SHIFT['clock_out_time'].strftime('%I:%M %p')}")
            
        except Exception as e:
            print(f"[ATTENDANCE] Error updating shift settings: {e}")
            # Keep defaults if parsing fails
            self.EARLY_SHIFT['clock_out_time'] = time(17, 0)
            self.REGULAR_SHIFT['clock_out_time'] = time(17, 15)
            self.min_clock_out_time = time(17, 0)
    
    def calculate_overtime_hours(self, clock_out_time, shift_clock_out_time):
        """Calculate overtime hours if employee clocks out 1+ hours after shift end time"""
        try:
            # Convert time objects to datetime for calculation
            today = datetime.now().date()
            clock_out_datetime = datetime.combine(today, clock_out_time)
            shift_end_datetime = datetime.combine(today, shift_clock_out_time)
            
            # Calculate the difference
            time_diff = clock_out_datetime - shift_end_datetime
            
            # Convert to total hours (including fractions)
            total_hours = time_diff.total_seconds() / 3600
            
            # Only count as OT if it's 1 hour or more
            if total_hours >= 1.0:
                # Return whole hours only (floor division)
                return int(total_hours)
            else:
                return 0
                
        except Exception as e:
            print(f"[ATTENDANCE] Error calculating overtime: {e}")
            return 0

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
    
    def determine_shift_and_type(self, nric, current_time=None):
        """Determine shift type and attendance action based on arrival time and employee role"""
        if current_time is None:
            current_time = self.get_current_time()
            
        current_time_only = current_time.time()
        
        # Get employee information including role
        employee = self.db.get_employee(nric)
        if not employee:
            return None, None, None
            
        employee_role = employee.get('roles', [])  # Default to Staff if no role specified
        
        # Get today's records for this employee
        today_records = self.get_employee_attendance_today(nric)
        
        # Check if employee has already clocked in today
        clock_in_record = None
        for record in today_records:
            if record.get('attendance_type') == 'clock' and record['status'] == 'in':
                clock_in_record = record
                break
        
        if clock_in_record:
            # Employee already clocked in, determine current shift based on role and clock-in time
            clock_in_time = datetime.fromisoformat(clock_in_record['timestamp']).time()
            
            if employee_role == 'Security':
                # Security: 7:00 AM - 7:00 PM, no clock-out time restrictions
                assigned_shift = {
                    'clock_in_before': time(7, 0),
                    'clock_out_time': None,  # No restriction for security
                    'name': 'Security Shift (7:00 AM - 7:00 PM)'
                }
            else:
                # Staff: Original logic based on clock-in time
                if clock_in_time < self.EARLY_SHIFT['clock_in_before']:
                    assigned_shift = self.EARLY_SHIFT
                else:
                    assigned_shift = self.REGULAR_SHIFT
            
            # Always allow clock out attempt - let clock_out_employee handle time validation
            return assigned_shift, 'clock', 'out'
        
        else:
            # First time today - determine shift based on current time and role
            if employee_role == 'Security':
                # Security shift: 7:00 AM - 7:00 PM
                security_shift = {
                    'clock_in_before': time(7, 0),
                    'clock_out_time': None,  # No restriction
                    'name': 'Security Shift (7:00 AM - 7:00 PM)'
                }
                
                # Calculate grace period time (7:00 AM + 15 minutes = 7:15 AM)
                grace_period_time = time(7, 15)
                
                if current_time_only < grace_period_time:
                    return security_shift, 'clock', 'in'
                else:
                    # Late if after 7:15 AM (grace period expired)
                    return security_shift, 'clock', 'in_late'
            else:
                # Staff: Original logic with grace period
                if current_time_only < self.EARLY_SHIFT['clock_in_before']:
                    return self.EARLY_SHIFT, 'clock', 'in'
                elif current_time_only < self.REGULAR_SHIFT['clock_in_before']:
                    return self.REGULAR_SHIFT, 'clock', 'in'
                else:
                    # Calculate grace period time (8:00 AM + 15 minutes = 8:15 AM)
                    regular_shift_with_grace = datetime.combine(
                        datetime.today(),
                        self.REGULAR_SHIFT['clock_in_before']
                    ) + timedelta(minutes=self.CLOCK_IN_GRACE_PERIOD_MINUTES)
                    grace_period_time = regular_shift_with_grace.time()
                    
                    if current_time_only < grace_period_time:
                        # Within grace period - not late
                        return self.REGULAR_SHIFT, 'clock', 'in'
                    else:
                        # After grace period - mark as late
                        return self.REGULAR_SHIFT, 'clock', 'in_late'
    
    def process_attendance(self, nric, method, attendance_mode, location_callback=None, is_late=False, shift_name=None, emergency_override=False):
        employee = self.db.get_employee(nric)
        if not employee:
            return False, f"Employee {nric} not found"

        if attendance_mode.upper() == 'CLOCK':
            # If shift_name is provided (from UI Security logic), use it
            if shift_name:
                shift = {'name': shift_name}
            else:
                current_time = self.get_current_time()
                shift, att_type, action = self.determine_shift_and_type(nric, current_time)
            # If is_late is provided, use it
            if is_late:
                return self.clock_in_employee(nric, method, shift, is_late=True)
            # If shift_name is provided, treat as clock in (for Security)
            if shift_name:
                return self.clock_in_employee(nric, method, shift, is_late=is_late)
            # Otherwise, use normal alternating logic
            if 'action' in locals():
                if action == 'in':
                    return self.clock_in_employee(nric, method, shift)
                elif action == 'in_late':
                    return self.clock_in_employee(nric, method, shift, is_late=True)
                elif action == 'out':
                    return self.clock_out_employee(nric, method, shift, emergency_override=emergency_override)
                else:
                    return False, f"Clock mode not available - use CHECK mode during work hours"
            else:
                # If emergency override is set, force clock out
                if emergency_override:
                    return self.clock_out_employee(nric, method, shift, emergency_override=True)
                # Fallback: treat as clock in
                return self.clock_in_employee(nric, method, shift)

        elif attendance_mode.upper() == 'CHECK':
            # CHECK mode: Simple toggle for office entry/exit without time restrictions
            result = self.toggle_check_attendance(nric, method, location_callback)
            # Handle both old and new return formats
            if len(result) == 3:
                return result[0], result[1]  # success, message (ignore record_id for now)
            else:
                return result

        return False, "Invalid attendance mode"
    
    def clock_in_employee(self, nric, method, shift, is_late=False):
        """Clock in employee for shift start"""
        employee = self.db.get_employee(nric)
        employee_role = employee.get('role', 'Staff')
        
        # Check if already clocked in today
        today_records = self.get_employee_attendance_today(nric)
        for record in today_records:
            if record.get('attendance_type') == 'clock' and record['status'] == 'in':
                return False, f"{employee['name']} ({employee_role}) is already clocked in for {shift['name']}"
        
        # Record clock-in with late flag
        current_time = self.get_current_time()
        record_id = self.db.record_attendance(nric, method, "in", "clock", current_time, late=is_late)
        
        # Return appropriate message based on role and timing
        if is_late:
            if employee_role == 'Security':
                return True, f"{employee['name']} (Security) LATE clock in (after 7:00 AM)"
            else:
                return True, f"{employee['name']} (Staff) LATE clock in (after 8:00 AM)"
        else:
            return True, f"{employee['name']} ({employee_role}) clocked in for {shift['name']}"
    
    def clock_out_employee(self, nric, method, shift, emergency_override=False):
        """Clock out employee for shift end with role-based time restrictions"""
        employee = self.db.get_employee(nric)
        employee_role = employee.get('role', 'Staff')
        
        # Check if clocked in today and get clock-in record
        today_records = self.get_employee_attendance_today(nric)
        clock_in_record = None
        for record in today_records:
            if record.get('attendance_type') == 'clock' and record['status'] == 'in':
                clock_in_record = record
                break
        
        if not clock_in_record:
            # For Security, check if there's a previous day night shift to clock out
            if employee_role == 'Security':
                from datetime import timedelta
                prev_date = (current_time - timedelta(days=1)).date()
                # Get yesterday's records
                prev_start = datetime.combine(prev_date, datetime.min.time())
                prev_end = datetime.combine(prev_date, datetime.max.time())
                prev_records = []
                
                # Get all attendance records for previous day
                all_records = self.db.get_attendance_by_date_range(prev_date.strftime('%Y-%m-%d'), prev_date.strftime('%Y-%m-%d'))
                prev_records = [r for r in all_records if r['nric'] == nric]
                
                # Check for night shift clock-in without clock-out
                night_shift_in = None
                has_clock_out = False
                for record in prev_records:
                    if record.get('attendance_type') == 'clock':
                        if record['status'] == 'in':
                            clock_time = datetime.fromisoformat(record['timestamp']).time()
                            if clock_time >= time(18, 0):  # Night shift
                                night_shift_in = record
                        elif record['status'] == 'out':
                            has_clock_out = True
                
                if night_shift_in and not has_clock_out:
                    # Allow night shift clock-out if it's 7:00 AM or later
                    if current_time_only >= time(7, 0):
                        # Calculate overtime for night shift
                        min_clock_out_time = time(7, 0)
                        overtime_hours = self.calculate_overtime_hours(current_time_only, min_clock_out_time)
                        
                        # Record clock-out for previous day night shift
                        record_id = self.db.record_attendance(nric, method, "out", "clock", current_time, overtime_hours=overtime_hours)
                        
                        base_message = f"{employee['name']} (Security) clocked out from Night Shift (7:00 PM - 7:00 AM)"
                        if overtime_hours > 0:
                            base_message += f" - OT {overtime_hours} hour{'s' if overtime_hours > 1 else ''}"
                        
                        return True, base_message
                    else:
                        return False, f"Cannot clock out before 7:00 AM (Night Shift)"
            
            return False, f"{employee['name']} ({employee_role}) hasn't clocked in today"
        
        # Check if already clocked out
        for record in today_records:
            if record.get('attendance_type') == 'clock' and record['status'] == 'out':
                return False, f"{employee['name']} ({employee_role}) is already clocked out"
        
        # Role-based clock-out time restrictions
        current_time = self.get_current_time()
        current_time_only = current_time.time()
        
        if employee_role == 'Security':
            # Security: Apply shift-based time restrictions
            from datetime import datetime
            
            # If there's no clock_in_record, this should have been handled by previous day night shift logic
            if not clock_in_record:
                return False, f"{employee['name']} (Security) hasn't clocked in today"
                
            clock_in_time = datetime.fromisoformat(clock_in_record['timestamp']).time()
            
            # Determine shift and minimum clock-out time
            if clock_in_time >= time(18, 0):  # Night shift (6:00 PM - 7:00 AM next day)
                min_clock_out_time = time(7, 0)  # 7:00 AM next day
                shift_name = "Night Shift (7:00 PM - 7:00 AM)"
                # Check if current time is appropriate for night shift clock-out (skip if emergency)
                if not emergency_override and current_time_only < min_clock_out_time:
                    min_time_str = min_clock_out_time.strftime("%I:%M %p")
                    return False, f"Cannot clock out before {min_time_str} ({shift_name})"
            else:  # Day shift (6:00 AM - 7:00 PM same day)
                min_clock_out_time = time(19, 0)  # 7:00 PM
                shift_name = "Day Shift (7:00 AM - 7:00 PM)"
                if not emergency_override and current_time_only < min_clock_out_time:
                    min_time_str = min_clock_out_time.strftime("%I:%M %p")
                    return False, f"Cannot clock out before {min_time_str} ({shift_name})"
            
            # Calculate overtime hours for security (or negative for early clock-out)
            overtime_hours = self.calculate_overtime_hours(current_time_only, min_clock_out_time)
            
            # Record clock-out with overtime information
            record_id = self.db.record_attendance(nric, method, "out", "clock", current_time, overtime_hours=overtime_hours)
            
            # Create clock out message with overtime if applicable
            if emergency_override:
                base_message = f"{employee['name']} (Security) 🚨 EMERGENCY CLOCK-OUT from {shift_name}"
            else:
                base_message = f"{employee['name']} (Security) clocked out from {shift_name}"
                if overtime_hours > 0:
                    base_message += f" - OT {overtime_hours} hour{'s' if overtime_hours > 1 else ''}"
            
            return True, base_message
        else:
            # Staff: Apply original time restrictions
            # Get clock-in time from the record
            from datetime import datetime
            clock_in_time = datetime.fromisoformat(clock_in_record['timestamp']).time()
            
            # Determine shift type and appropriate minimum clock-out time
            if clock_in_time < time(8, 0):  # Clocked in before 8:00 AM = Early Shift
                shift_name = self.EARLY_SHIFT['name']
                min_clock_out_time = self.EARLY_SHIFT['clock_out_time']
            else:  # Clocked in at 8:00 AM or later = Regular Shift (including late arrivals)
                shift_name = self.REGULAR_SHIFT['name']
                min_clock_out_time = self.REGULAR_SHIFT['clock_out_time']
            
            # Check if current time is before minimum clock-out time for this shift (skip if emergency)
            if not emergency_override and current_time_only < min_clock_out_time:
                min_time_str = min_clock_out_time.strftime("%I:%M %p")
                return False, f"Cannot clock out before {min_time_str} ({shift_name})"
            
            # Calculate overtime hours (or negative for early clock-out)
            overtime_hours = self.calculate_overtime_hours(current_time_only, min_clock_out_time)
            
            # Record clock-out with overtime information
            record_id = self.db.record_attendance(nric, method, "out", "clock", current_time, overtime_hours=overtime_hours)
            
            # Create clock out message with overtime if applicable
            if emergency_override:
                base_message = f"{employee['name']} (Staff) 🚨 EMERGENCY CLOCK-OUT from {shift_name}"
            else:
                base_message = f"{employee['name']} (Staff) clocked out from {shift_name}"
                if overtime_hours > 0:
                    base_message += f" - OT {overtime_hours} hour{'s' if overtime_hours > 1 else ''}"
            
            return True, base_message
    
    def toggle_check_attendance(self, nric, method, location_callback=None):
        """Toggle check in/out for office entry/exit during work hours"""
        employee = self.db.get_employee(nric)
        today_records = self.get_employee_attendance_today(nric)
        
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
            record_id = self.db.record_attendance(nric, method, "out", "check", current_time)
            
            # If location callback is provided, trigger location selection
            if location_callback:
                location_callback(record_id, nric)
                
            return True, f"{employee['name']} checked out of office", record_id
        else:
            # Toggle based on last check status
            if last_check_record['status'] == 'in':
                # CHECK OUT - need location selection
                record_id = self.db.record_attendance(nric, method, "out", "check", current_time)
                
                # If location callback is provided, trigger location selection
                if location_callback:
                    location_callback(record_id, nric)
                
                return True, f"{employee['name']} checked out of office", record_id
            else:
                # CHECK IN
                record_id = self.db.record_attendance(nric, method, "in", "check", current_time)
                return True, f"{employee['name']} checked into office", record_id
    
    def check_in_employee(self, nric, method="manual"):
        """Check in an employee"""
        # Verify employee exists
        employee = self.db.get_employee(nric)
        if not employee:
            return False, f"Employee {nric} not found"
        
        # Check if already checked in today
        today_records = self.get_employee_attendance_today(nric)
        if today_records:
            last_record = today_records[0]  # Most recent record
            if last_record['status'] == 'in':
                return False, f"{employee['name']} is already checked in"
        
        # Record check-in
        record_id = self.db.record_attendance(nric, method, "in")
        return True, f"{employee['name']} checked in successfully"
    
    def check_out_employee(self, nric, method="manual"):
        """Check out an employee"""
        # Verify employee exists
        employee = self.db.get_employee(nric)
        if not employee:
            return False, f"Employee {nric} not found"
        
        # Check if checked in today
        today_records = self.get_employee_attendance_today(nric)
        if not today_records:
            return False, f"{employee['name']} hasn't checked in today"
        
        last_record = today_records[0]  # Most recent record
        if last_record['status'] == 'out':
            return False, f"{employee['name']} is already checked out"
        
        # Record check-out
        record_id = self.db.record_attendance(nric, method, "out")
        return True, f"{employee['name']} checked out successfully"
    
    def toggle_attendance(self, nric, method="manual"):
        """Toggle attendance (check in if out, check out if in)"""
        employee = self.db.get_employee(nric)
        if not employee:
            return False, f"Employee {nric} not found"
        
        today_records = self.get_employee_attendance_today(nric)
        
        if not today_records:
            # No records today, check in
            return self.check_in_employee(nric, method)
        else:
            last_record = today_records[0]
            if last_record['status'] == 'in':
                # Last status was in, check out
                return self.check_out_employee(nric, method)
            else:
                # Last status was out, check in
                return self.check_in_employee(nric, method)
    
    def get_employee_attendance_today(self, nric):
        """Get today's attendance records for a specific employee"""
        all_today = self.db.get_attendance_today()
        return [record for record in all_today if record['nric'] == nric]

    def get_attendance_summary_today(self):
        """Get summary of today's attendance"""
        attendance_records = self.db.get_attendance_today()
        
        # Group by employee
        employee_status = {}
        for record in attendance_records:
            emp_id = record['nric']
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
            daily_attendance[date].add(record['nric'])
        
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
            emp_id = record['nric']
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
