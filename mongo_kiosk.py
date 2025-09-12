#!/usr/bin/env python3
"""
MongoDB-Enabled Simple Kiosk Mode Attendance System
Optimized for keyboard and touch operation without mouse
Uses MongoDB instead of SQLite
"""

import customtkinter as ctk
import tkinter as tk
import cv2
import time
import ctypes
import os
import csv
from tkinter import messagebox
from PIL import Image, ImageTk
from datetime import datetime

from core.mongodb_manager import MongoDBManager  # Updated import
from core.face_recognition import FaceRecognitionSystem, CameraManager
from core.barcode_scanner import BarcodeScanner
from core.attendance import AttendanceManager
from core.mongo_location_manager import MongoLocationManager  # Updated import
from core.location_selector import LocationSelector

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MongoKioskApp:
    def __init__(self):
        # Make application DPI-aware (must be done before creating tkinter window)
        try:
            # Tell Windows this app is DPI-aware
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            print("[INIT DEBUG] Successfully set DPI awareness")
        except:
            print("[INIT DEBUG] Could not set DPI awareness (not critical)")
        
        self.root = ctk.CTk()
        self.root.title("MongoDB Attendance Kiosk")
        
        # Kiosk mode settings
        self.setup_kiosk_mode()
        
        # Initialize MongoDB components
        print("[INIT DEBUG] Initializing MongoDB components...")
        try:
            self.db = MongoDBManager()
            print("[INIT DEBUG] MongoDB manager initialized")
            
            self.attendance_manager = AttendanceManager(self.db)
            print("[INIT DEBUG] Attendance manager initialized")
            
            self.location_manager = MongoLocationManager(self.db)
            print("[INIT DEBUG] MongoDB location manager initialized")
            
        except Exception as e:
            print(f"[INIT ERROR] Failed to initialize MongoDB: {e}")
            messagebox.showerror("Database Error", 
                               f"Failed to connect to MongoDB:\n{e}\n\nPlease check your mongo_config.py file.")
            return
        
        # Initialize other components
        self.face_recognition = FaceRecognitionSystem()
        print("[INIT DEBUG] Face recognition system initialized")
        
        self.camera_manager = CameraManager()
        print("[INIT DEBUG] Camera manager initialized")
        
        self.barcode_scanner = BarcodeScanner()
        print("[INIT DEBUG] Barcode scanner initialized")
        
        # GUI state variables
        self.camera_active = False
        self.current_mode = "auto"  # auto, manual
        self.attendance_mode = "CLOCK"  # CLOCK or CHECK
        self.auto_timeout = 3  # seconds to show result
        self.last_history_update = 0  # for periodic updates
        
        # Scanning cooldown to prevent rapid-fire scanning
        self.last_scan_time = 0  # timestamp of last successful scan
        self.scan_cooldown = 5.0  # seconds between scans
        self.last_face_scan = 0  # separate cooldown for face recognition
        self.last_qr_scan = 0  # separate cooldown for QR/barcode
        
        # Create GUI
        self.create_interface()
        
        # Set initial mode appearance
        self.set_attendance_mode("CLOCK")
        
        # Load known faces
        self.load_known_faces()
        
        # Start camera automatically
        self.start_camera()
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Start update loop
        self.update_loop()
    
    def setup_kiosk_mode(self):
        """Configure for kiosk operation"""
        # Get actual screen size (handling DPI scaling)
        try:
            # Get actual screen dimensions bypassing DPI scaling
            user32 = ctypes.windll.user32
            screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            screen_width, screen_height = screensize
            print(f"[KIOSK DEBUG] True screen dimensions (via Windows API): {screen_width}x{screen_height}")
        except:
            # Fallback to tkinter method
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            print(f"[KIOSK DEBUG] Fallback screen dimensions (via tkinter): {screen_width}x{screen_height}")
        
        try:
            # Method 1: Full override with true resolution
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")
            self.root.attributes('-fullscreen', True)
            self.root.attributes('-topmost', True)
            self.root.overrideredirect(True)  # Remove all window decorations
            print(f"[KIOSK DEBUG] Using override redirect method with true resolution")
        except Exception as e:
            print(f"[KIOSK DEBUG] Override method failed: {e}")
            try:
                # Method 2: Standard fullscreen with true resolution
                self.root.geometry(f"{screen_width}x{screen_height}+0+0")
                self.root.attributes('-fullscreen', True)
                self.root.attributes('-topmost', True)
                self.root.state('zoomed')
                print(f"[KIOSK DEBUG] Using standard fullscreen method with true resolution")
            except Exception as e2:
                print(f"[KIOSK DEBUG] Standard fullscreen failed: {e2}")
                # Method 3: Fallback maximized
                self.root.state('zoomed')
                self.root.attributes('-topmost', True)
                print(f"[KIOSK DEBUG] Using fallback maximized method")
        
        # Force focus and update
        self.root.focus_force()
        self.root.update()
        self.root.lift()
        self.root.grab_set()
        
        # Check final size after a moment
        self.root.after(100, self.check_final_size)
        self.root.after(500, self.ensure_focus)
    
    def check_final_size(self):
        """Check and report the final window size"""
        final_width = self.root.winfo_width()
        final_height = self.root.winfo_height()
        print(f"[KIOSK DEBUG] Final window size: {final_width}x{final_height}")
    
    def ensure_focus(self):
        """Ensure the application has focus and can receive keyboard input"""
        print("[FOCUS DEBUG] Ensuring application has focus...")
        try:
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.focus_force()
            self.root.focus_set()
            self.root.update()
            print("[FOCUS DEBUG] ✓ Focus management completed")
        except Exception as e:
            print(f"[FOCUS DEBUG] ✗ Focus management failed: {e}")
    
    def create_interface(self):
        """Create the main interface"""
        # Main container
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)
        
        # Header with MongoDB indicator
        self.create_header()
        
        # Content area with camera and controls
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Left side - Camera feed (smaller, fixed width)
        self.camera_frame = ctk.CTkFrame(self.content_frame, width=480, height=400)
        self.camera_frame.pack(side="left", fill="y", padx=(10, 20), pady=10)
        self.camera_frame.pack_propagate(False)
        
        self.camera_label = ctk.CTkLabel(
            self.camera_frame, 
            text="Starting Camera...",
            font=ctk.CTkFont(size=20)
        )
        self.camera_label.pack(expand=True, padx=15, pady=15)
        
        # Right side - Attendance history (larger, expandable)
        self.control_frame = ctk.CTkFrame(self.content_frame)
        self.control_frame.pack(side="right", fill="both", expand=True, padx=(20, 10), pady=10)
        
        self.create_controls()
        
        # Bottom - Status and messages
        self.create_status_area()
    
    def create_header(self):
        """Create header with title and time"""
        header_frame = ctk.CTkFrame(self.main_frame, height=120)
        header_frame.pack(fill="x", padx=30, pady=20)
        header_frame.pack_propagate(False)
        
        # Title with MongoDB indicator
        title_label = ctk.CTkLabel(
            header_frame,
            text="ATTENDANCE SYSTEM (MongoDB)",
            font=ctk.CTkFont(size=42, weight="bold")
        )
        title_label.pack(side="left", padx=30, pady=30)
        
        # Database status indicator
        db_status_label = ctk.CTkLabel(
            header_frame,
            text="🍃 MongoDB Connected",
            font=ctk.CTkFont(size=16),
            text_color="green"
        )
        db_status_label.pack(side="left", padx=10, pady=30)
        
        # Time display
        self.time_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=24)
        )
        self.time_label.pack(side="right", padx=30, pady=30)
    
    def create_controls(self):
        """Create control panels with separate interfaces for CLOCK and CHECK modes"""
        # Mode selection frame at top
        mode_selection_frame = ctk.CTkFrame(self.control_frame, height=80)
        mode_selection_frame.pack(fill="x", padx=10, pady=10)
        mode_selection_frame.pack_propagate(False)
        
        mode_title = ctk.CTkLabel(
            mode_selection_frame,
            text="SELECT MODE:",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        mode_title.pack(side="left", padx=20, pady=20)
        
        # Mode buttons
        self.clock_btn = ctk.CTkButton(
            mode_selection_frame,
            text="🕐 CLOCK MODE (1)",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=180,
            height=50,
            command=lambda: self.set_attendance_mode("CLOCK")
        )
        self.clock_btn.pack(side="left", padx=10, pady=15)
        
        self.check_btn = ctk.CTkButton(
            mode_selection_frame,
            text="✅ CHECK MODE (2)",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=180,
            height=50,
            command=lambda: self.set_attendance_mode("CHECK")
        )
        self.check_btn.pack(side="left", padx=10, pady=15)
        
        # Cooldown status display
        self.cooldown_label = ctk.CTkLabel(
            mode_selection_frame,
            text="● Ready to scan",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="green"
        )
        self.cooldown_label.pack(side="right", padx=20, pady=20)
        
        # Create both interface panels
        self.create_clock_interface()
        self.create_check_interface()
        
        # Load initial attendance data
        self.update_attendance_history()
    
    def create_clock_interface(self):
        """Create the CLOCK mode interface for shift management"""
        self.clock_interface = ctk.CTkFrame(self.control_frame)
        
        # CLOCK mode title
        clock_title_frame = ctk.CTkFrame(self.clock_interface, fg_color="transparent")
        clock_title_frame.pack(fill="x", padx=10, pady=10)
        
        clock_title = ctk.CTkLabel(
            clock_title_frame,
            text="🕐 SHIFT MANAGEMENT",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=("green", "lightgreen")
        )
        clock_title.pack()
        
        # CLOCK mode attendance history
        self.clock_history_frame = ctk.CTkScrollableFrame(
            self.clock_interface,
            width=600,
            height=520,
            fg_color=("gray95", "gray10"),
            border_width=2,
            border_color=("green", "darkgreen")
        )
        self.clock_history_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # CLOCK mode controls
        clock_controls = ctk.CTkFrame(self.clock_interface, height=80)
        clock_controls.pack(fill="x", padx=10, pady=10)
        clock_controls.pack_propagate(False)
        
        self.clock_manual_btn = ctk.CTkButton(
            clock_controls,
            text="⌨️ MANUAL CLOCK ENTRY (Enter)",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=250,
            height=50,
            command=self.show_manual_entry
        )
        self.clock_manual_btn.pack(side="left", padx=10, pady=15)
        
        self.clock_status_label = ctk.CTkLabel(
            clock_controls,
            text="Scan face or QR code to CLOCK IN/OUT",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="green"
        )
        self.clock_status_label.pack(side="right", padx=20, pady=15)
    
    def create_check_interface(self):
        """Create the CHECK mode interface for office entry/exit"""
        self.check_interface = ctk.CTkFrame(self.control_frame)
        
        # CHECK mode title
        check_title_frame = ctk.CTkFrame(self.check_interface, fg_color="transparent")
        check_title_frame.pack(fill="x", padx=10, pady=10)
        
        check_title = ctk.CTkLabel(
            check_title_frame,
            text="✅ OFFICE ENTRY/EXIT",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=("blue", "lightblue")
        )
        check_title.pack()
        
        # CHECK mode attendance history
        self.check_history_frame = ctk.CTkScrollableFrame(
            self.check_interface,
            width=600,
            height=520,
            fg_color=("gray95", "gray10"),
            border_width=2,
            border_color=("blue", "darkblue")
        )
        self.check_history_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # CHECK mode controls
        check_controls = ctk.CTkFrame(self.check_interface, height=80)
        check_controls.pack(fill="x", padx=10, pady=10)
        check_controls.pack_propagate(False)
        
        self.check_manual_btn = ctk.CTkButton(
            check_controls,
            text="⌨️ MANUAL CHECK ENTRY (Enter)",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=250,
            height=50,
            command=self.show_manual_entry
        )
        self.check_manual_btn.pack(side="left", padx=10, pady=15)
        
        self.check_status_label = ctk.CTkLabel(
            check_controls,
            text="Scan face or QR code to CHECK IN/OUT",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="blue"
        )
        self.check_status_label.pack(side="right", padx=20, pady=15)
    
    def create_status_area(self):
        """Create status and message area"""
        self.status_frame = ctk.CTkFrame(self.main_frame, height=100)
        self.status_frame.pack(fill="x", padx=30, pady=20)
        self.status_frame.pack_propagate(False)
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="● READY - Please position yourself in front of the camera",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="green"
        )
        self.status_label.pack(pady=15)
        
        # Help information
        help_text = "⌨️ SHORTCUTS: 1=Clock Mode • 2=Check Mode • Enter=Manual Entry • +=Camera • *=Export • -=Exit"
        help_label = ctk.CTkLabel(
            self.status_frame,
            text=help_text,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        help_label.pack(pady=5)
        
        # Message area (initially hidden)
        self.message_frame = ctk.CTkFrame(self.main_frame)
        self.message_label = ctk.CTkLabel(
            self.message_frame,
            text="",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.message_label.pack(pady=20)
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Shortcuts
        self.root.bind('<F1>', lambda e: self.show_help())
        self.root.bind('<F4>', lambda e: self.toggle_kiosk_mode())
        self.root.bind('<Escape>', lambda e: self.clear_message())
        self.root.bind('<Alt-F4>', lambda e: self.quit_app())
        
        # Numpad shortcuts
        self.root.bind('<KP_Subtract>', lambda e: self.quit_app())
        self.root.bind('<minus>', lambda e: self.quit_app())
        self.root.bind('<KP_Add>', lambda e: self.toggle_camera())
        self.root.bind('<plus>', lambda e: self.toggle_camera())
        self.root.bind('<KP_Multiply>', lambda e: self.export_daily_csv())
        self.root.bind('<asterisk>', lambda e: self.export_daily_csv())
        
        # Additional shortcuts
        self.root.bind('<Return>', lambda e: self.show_manual_entry())
        self.root.bind('<KP_Enter>', lambda e: self.show_manual_entry())
        
        # Mode switching
        self.root.bind('<Key-1>', lambda e: self.set_attendance_mode("CLOCK"))
        self.root.bind('<KP_1>', lambda e: self.set_attendance_mode("CLOCK"))
        self.root.bind('<Key-2>', lambda e: self.set_attendance_mode("CHECK"))
        self.root.bind('<KP_2>', lambda e: self.set_attendance_mode("CHECK"))
        
        # Focus management
        self.root.focus_set()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        self.root.lift()
        
        print("[KEYBOARD DEBUG] Keyboard shortcuts configured")
    
    # Include all other methods from the original simple_kiosk.py
    # (show_manual_entry, process_manual_entry, load_known_faces, etc.)
    # These would be copied from the original file...
    
    def show_manual_entry(self):
        """Show manual entry dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Manual Entry")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 400,
            self.root.winfo_rooty() + 200
        ))
        
        # Entry widgets
        tk.Label(dialog, text="Enter Employee ID:", font=("Arial", 16)).pack(pady=20)
        
        # Create validation function for numbers only
        def validate_input(char, current_text):
            return char.isdigit() and len(current_text) < 10
        
        vcmd = (dialog.register(validate_input), '%S', '%P')
        
        entry = tk.Entry(dialog, font=("Arial", 14), width=20, justify="center",
                        validate='key', validatecommand=vcmd)
        entry.pack(pady=10)
        entry.focus_set()
        
        def submit():
            employee_id = entry.get().strip()
            dialog.destroy()
            if employee_id and employee_id.isdigit():
                self.process_manual_entry(employee_id)
            elif employee_id:
                self.show_error_message("❌ Please enter numbers only")
            else:
                self.show_error_message("❌ Please enter an Employee ID")
        
        def cancel():
            dialog.destroy()
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Submit", font=("Arial", 12), 
                 command=submit, width=10).pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", font=("Arial", 12), 
                 command=cancel, width=10).pack(side="left", padx=10)
        
        # Bind keys
        entry.bind('<Return>', lambda e: submit())
        dialog.bind('<Escape>', lambda e: cancel())
    
    def process_manual_entry(self, employee_id):
        """Process manual employee ID entry"""
        employee = self.db.get_employee(employee_id)
        if employee:
            # Create location callback for CHECK mode checkout
            location_callback = None
            if self.attendance_mode == "CHECK":
                location_callback = self.handle_checkout_location_selection
            
            success, message = self.attendance_manager.process_attendance(
                employee_id, "manual", self.attendance_mode, location_callback
            )
            if success:
                self.show_success_message(f"✅ {message}")
            else:
                self.show_error_message(f"❌ {message}")
        else:
            self.show_employee_not_found_dialog(employee_id)
    
    def handle_checkout_location_selection(self, attendance_id, employee_id):
        """Handle location selection for check-out"""
        def on_location_selected(location):
            if location:
                self.location_manager.save_checkout_location(attendance_id, employee_id, location)
                self.show_success_message(f"✅ Location saved: {location.get('display_name', 'Unknown')}")
            else:
                self.show_error_message("❌ No location selected")
        
        # Open location selector dialog
        LocationSelector(
            parent=self.root,
            employee_id=employee_id,
            callback=on_location_selected
        )
    
    def load_known_faces(self):
        """Load known faces from MongoDB"""
        print("[FACE DEBUG] Loading known faces from MongoDB...")
        employees_with_faces = self.db.get_all_face_images()
        print(f"[FACE DEBUG] Found {len(employees_with_faces)} employees with face images")
        for emp in employees_with_faces:
            print(f"[FACE DEBUG] - {emp['name']} ({emp['employee_id']}): {emp.get('face_image_path', 'No image path')}")
        self.face_recognition.load_known_faces(employees_with_faces)
    
    def update_attendance_history(self):
        """Update the attendance history display for the current mode"""
        # Determine which history frame to update based on current mode
        if self.attendance_mode == "CLOCK":
            history_frame = self.clock_history_frame
            mode_filter = "clock"
        else:  # CHECK
            history_frame = self.check_history_frame
            mode_filter = "check"
        
        # Clear existing history
        for widget in history_frame.winfo_children():
            widget.destroy()
        
        # Get today's attendance from MongoDB
        attendance_records = self.db.get_attendance_today()
        
        # Filter for current mode
        mode_records = []
        current_date = datetime.now().strftime("%Y-%m-%d")
        for record in attendance_records:
            record_date = record['timestamp'][:10]
            if record_date == current_date and record.get('attendance_type') == mode_filter:
                mode_records.append(record)
        
        print(f"[ATTENDANCE DEBUG] Found {len(mode_records)} {mode_filter} records for today")
        
        if not mode_records:
            no_records_label = ctk.CTkLabel(
                history_frame,
                text=f"No {mode_filter.upper()} records for {current_date}",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            no_records_label.pack(pady=20)
            return
        
        # Group and display records by employee
        employee_records = {}
        for record in mode_records:
            emp_id = record['employee_id']
            if emp_id not in employee_records:
                employee_records[emp_id] = {
                    'name': record['name'],
                    'records': []
                }
            employee_records[emp_id]['records'].append(record)
        
        # Sort records by time for each employee
        for emp_id in employee_records:
            employee_records[emp_id]['records'].sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Display records
        for emp_id, data in employee_records.items():
            self.create_employee_history_section(emp_id, data, history_frame)
    
    def create_employee_history_section(self, employee_id, data, history_frame):
        """Create a section showing all attendance records for one employee"""
        border_color = ("green", "lightgreen") if self.attendance_mode == "CLOCK" else ("blue", "lightblue")
        main_frame = ctk.CTkFrame(
            history_frame, 
            border_width=2, 
            border_color=border_color,
            fg_color=("gray95", "gray15")
        )
        main_frame.pack(fill="x", padx=8, pady=12)
        
        # Employee header
        header_frame = ctk.CTkFrame(main_frame, fg_color=("blue", "darkblue"))
        header_frame.pack(fill="x", padx=6, pady=6)
        
        info_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_container.pack(fill="x", padx=12, pady=8)
        
        # Employee name
        name_label = ctk.CTkLabel(
            info_container,
            text=f"👤 {data['name']}",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white",
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)
        
        # Employee ID
        id_label = ctk.CTkLabel(
            info_container,
            text=f"ID: {employee_id}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="lightgray",
            anchor="e"
        )
        id_label.pack(side="right", padx=10)
        
        # Current status
        latest_record = data['records'][0]
        attendance_type = latest_record.get('attendance_type', 'check')
        if attendance_type == 'clock':
            current_status = "CLOCKED IN" if latest_record['status'] == 'in' else "CLOCKED OUT"
        else:
            current_status = "CHECKED IN" if latest_record['status'] == 'in' else "CHECKED OUT"
        
        status_color = "lightgreen" if latest_record['status'] == 'in' else "red"
        status_icon = "🟢" if latest_record['status'] == 'in' else "🔴"
        
        status_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=12, pady=5)
        
        status_label = ctk.CTkLabel(
            status_frame,
            text=f"{status_icon} CURRENT STATUS: {current_status}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=status_color,
            anchor="center"
        )
        status_label.pack(pady=3)
        
        # Records list
        records_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        records_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        for i, record in enumerate(data['records']):
            self.create_single_record_entry(records_frame, record, i)
    
    def create_single_record_entry(self, parent, record, index):
        """Create a single attendance record entry"""
        bg_color = ("gray90", "gray20") if index % 2 == 0 else ("white", "gray25")
        record_frame = ctk.CTkFrame(parent, fg_color=bg_color, height=50)
        record_frame.pack(fill="x", pady=3, padx=5)
        record_frame.pack_propagate(False)
        
        # Parse timestamp
        record_time = datetime.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
        time_str = record_time.strftime("%H:%M:%S")
        
        # Status
        status_text = "IN" if record['status'] == 'in' else "OUT"
        status_color = "lightgreen" if record['status'] == 'in' else "red"
        status_icon = "🟢" if record['status'] == 'in' else "🔴"
        
        # Method
        method_icons = {
            'face_recognition': '👤 Face Recognition',
            'qr_code': '📱 QR/Barcode', 
            'manual': '⌨️ Manual Entry'
        }
        method_text = method_icons.get(record['method'], f"📋 {record['method']}")
        
        # Layout
        info_frame = ctk.CTkFrame(record_frame, fg_color="transparent")
        info_frame.pack(fill="both", expand=True, padx=15, pady=8)
        
        # Time
        time_frame = ctk.CTkFrame(info_frame, fg_color="transparent", width=120)
        time_frame.pack(side="left", fill="y")
        time_frame.pack_propagate(False)
        
        time_label = ctk.CTkLabel(
            time_frame,
            text=time_str,
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w"
        )
        time_label.pack(pady=2)
        
        # Status
        status_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        status_frame.pack(side="left", fill="both", expand=True, padx=20)
        
        attendance_type = record.get('attendance_type', 'CLOCK').upper()
        
        status_label = ctk.CTkLabel(
            status_frame,
            text=f"{status_icon} {attendance_type} {status_text}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=status_color,
            anchor="center"
        )
        status_label.pack(expand=True)
        
        # Method
        method_frame = ctk.CTkFrame(info_frame, fg_color="transparent", width=150)
        method_frame.pack(side="right", fill="y")
        method_frame.pack_propagate(False)
        
        method_label = ctk.CTkLabel(
            method_frame,
            text=method_text,
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40"),
            anchor="e"
        )
        method_label.pack(expand=True)
    
    def start_camera(self):
        """Start camera"""
        print("[CAMERA DEBUG] Attempting to start camera...")
        if self.camera_manager.start_camera():
            self.camera_active = True
            print("[CAMERA DEBUG] Camera started successfully")
        else:
            print("[CAMERA DEBUG] Failed to start camera")
            self.show_error_message("Cannot start camera")
    
    def stop_camera(self):
        """Stop camera"""
        print("[CAMERA DEBUG] Stopping camera...")
        self.camera_manager.stop_camera()
        self.camera_active = False
        self.camera_label.configure(image="", text="📷 Camera Off\n\nPress Numpad + to turn on")
        print("[CAMERA DEBUG] Camera stopped")
    
    def toggle_camera(self):
        """Toggle camera on/off"""
        if self.camera_active:
            self.stop_camera()
            self.show_success_message("📷 Camera turned OFF (Press Numpad + to turn back on)")
        else:
            self.start_camera()
            if self.camera_active:
                self.show_success_message("📷 Camera turned ON")
    
    def set_attendance_mode(self, mode):
        """Set the attendance mode and switch interfaces"""
        self.attendance_mode = mode
        
        # Hide both interfaces
        self.clock_interface.pack_forget()
        self.check_interface.pack_forget()
        
        # Update buttons and show appropriate interface
        if mode == "CLOCK":
            self.clock_btn.configure(fg_color=("green", "darkgreen"))
            self.check_btn.configure(fg_color=("gray70", "gray30"))
            self.clock_interface.pack(fill="both", expand=True, padx=10, pady=10)
        else:  # CHECK
            self.clock_btn.configure(fg_color=("gray70", "gray30"))
            self.check_btn.configure(fg_color=("blue", "darkblue"))
            self.check_interface.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.update_attendance_history()
        print(f"[MODE DEBUG] Switched to {mode} mode")
    
    def show_success_message(self, message):
        """Show success message"""
        self.message_frame.pack(fill="x", padx=30, pady=10)
        self.message_label.configure(text=message, text_color="green")
        self.status_label.configure(text="● SUCCESS", text_color="green")
        
        self.update_attendance_history()
        self.root.after(self.auto_timeout * 1000, self.clear_message)
    
    def show_error_message(self, message):
        """Show error message"""
        self.message_frame.pack(fill="x", padx=30, pady=10)
        self.message_label.configure(text=message, text_color="red")
        self.status_label.configure(text="● ERROR", text_color="red")
        
        self.root.after(self.auto_timeout * 1000, self.clear_message)
    
    def clear_message(self):
        """Clear status message"""
        self.message_frame.pack_forget()
        self.status_label.configure(
            text="● READY - Please position yourself in front of the camera",
            text_color="green"
        )
    
    def show_employee_not_found_dialog(self, employee_id):
        """Show error dialog for employee not found"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Employee Not Found")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 500,
            self.root.winfo_rooty() + 300
        ))
        
        dialog.configure(bg='#ff4444')
        
        main_frame = tk.Frame(dialog, bg='#ff4444')
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="❌", font=("Arial", 32), 
                bg='#ff4444', fg='white').pack(pady=10)
        
        tk.Label(main_frame, text="EMPLOYEE NOT FOUND", 
                font=("Arial", 14, "bold"), bg='#ff4444', fg='white').pack()
        
        tk.Label(main_frame, text=f"Employee ID: {employee_id}", 
                font=("Arial", 12), bg='#ff4444', fg='white').pack(pady=5)
        
        ok_button = tk.Button(main_frame, text="OK", font=("Arial", 12, "bold"),
                             command=dialog.destroy, width=10,
                             bg='white', fg='#ff4444')
        ok_button.pack(pady=15)
        ok_button.focus_set()
        
        dialog.bind('<Return>', lambda e: dialog.destroy())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
        dialog.after(5000, dialog.destroy)
    
    def export_daily_csv(self):
        """Export today's records to CSV"""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            attendance_records = self.db.get_attendance_today()
            
            if not attendance_records:
                self.show_error_message("📄 No attendance records found for today")
                return
            
            # Create exports directory
            os.makedirs("exports", exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exports/attendance_{current_date}_{timestamp}.csv"
            
            # Write CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Employee_ID', 'Employee_Name', 'Date', 'Time', 'Status', 'Method']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for record in sorted(attendance_records, key=lambda x: (x['name'], x['timestamp'])):
                    timestamp_obj = datetime.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
                    date_part = timestamp_obj.strftime("%Y-%m-%d")
                    time_part = timestamp_obj.strftime("%H:%M:%S")
                    
                    status = f"{record.get('attendance_type', 'CHECK').upper()} {record['status'].upper()}"
                    
                    method_map = {
                        'face_recognition': 'Face Recognition',
                        'qr_code': 'QR/Barcode Scan',
                        'manual': 'Manual Entry'
                    }
                    method = method_map.get(record['method'], record['method'])
                    
                    writer.writerow({
                        'Employee_ID': record['employee_id'],
                        'Employee_Name': record['name'],
                        'Date': date_part,
                        'Time': time_part,
                        'Status': status,
                        'Method': method
                    })
            
            self.show_success_message(f"📄 Exported {len(attendance_records)} records\nSaved to: {filename}")
            
        except Exception as e:
            print(f"[CSV EXPORT] Error: {e}")
            self.show_error_message(f"📄 Export failed: {str(e)}")
    
    def process_camera(self):
        """Process camera feed and detect faces/QR codes"""
        frame = self.camera_manager.get_frame()
        if frame is None:
            return
        
        # Resize for display
        height, width = frame.shape[:2]
        display_width = 450
        display_height = int(height * display_width / width)
        max_height = 350
        if display_height > max_height:
            display_height = max_height
            display_width = int(width * display_height / height)
        display_frame = cv2.resize(frame, (display_width, display_height))
        
        # Face recognition with cooldown
        current_time = time.time()
        recognized_faces = self.face_recognition.process_video_frame(frame)
        
        for face in recognized_faces:
            if face['employee_id']:
                if current_time - self.last_face_scan < self.scan_cooldown:
                    continue
                
                self.last_face_scan = current_time
                employee = self.db.get_employee(face['employee_id'])
                if employee:
                    location_callback = None
                    if self.attendance_mode == "CHECK":
                        location_callback = self.handle_checkout_location_selection
                    
                    success, message = self.attendance_manager.process_attendance(
                        face['employee_id'], "face_recognition", self.attendance_mode, location_callback
                    )
                    
                    if success:
                        self.show_success_message(f"👤 {message}")
                    else:
                        self.show_error_message(f"👤 {message}")
                return
        
        # QR/Barcode scanning with cooldown
        qr_data = self.barcode_scanner.scan_frame(frame)
        if qr_data and current_time - self.last_qr_scan >= self.scan_cooldown:
            self.last_qr_scan = current_time
            employee = self.db.get_employee(qr_data)
            if employee:
                location_callback = None
                if self.attendance_mode == "CHECK":
                    location_callback = self.handle_checkout_location_selection
                
                success, message = self.attendance_manager.process_attendance(
                    qr_data, "qr_code", self.attendance_mode, location_callback
                )
                
                if success:
                    self.show_success_message(f"📱 {message}")
                else:
                    self.show_error_message(f"📱 {message}")
            else:
                self.show_error_message(f"📱 Employee not found: {qr_data}")
            return
        
        # Draw face boxes if detected
        if recognized_faces:
            display_frame = self.face_recognition.draw_face_boxes(display_frame, recognized_faces)
        
        # Convert and display frame
        frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        frame_pil = Image.fromarray(frame_rgb)
        frame_tk = ImageTk.PhotoImage(frame_pil)
        
        self.camera_label.configure(image=frame_tk, text="")
        self.camera_label.image = frame_tk
    
    def update_scanning_status(self):
        """Update scanning status display"""
        current_time = time.time()
        face_cooldown = max(0, self.scan_cooldown - (current_time - self.last_face_scan))
        qr_cooldown = max(0, self.scan_cooldown - (current_time - self.last_qr_scan))
        
        if face_cooldown > 0 or qr_cooldown > 0:
            max_cooldown = max(face_cooldown, qr_cooldown)
            self.cooldown_label.configure(text=f"⏳ Cooldown ({max_cooldown:.1f}s)", text_color="orange")
        else:
            self.cooldown_label.configure(text="● Ready to scan", text_color="green")
    
    def update_loop(self):
        """Main update loop"""
        # Update time
        current_time = datetime.now().strftime("%A, %B %d, %Y - %H:%M:%S")
        self.time_label.configure(text=current_time)
        
        # Update scanning status
        self.update_scanning_status()
        
        # Update attendance history periodically
        current_timestamp = time.time()
        if current_timestamp - self.last_history_update > 30:
            self.update_attendance_history()
            self.last_history_update = current_timestamp
        
        # Process camera
        if self.camera_active:
            self.process_camera()
        
        # Schedule next update
        self.root.after(33, self.update_loop)
    
    def quit_app(self):
        """Quit application with confirmation"""
        if hasattr(self, 'db') and self.db:
            self.db.close_connection()
        if self.camera_active:
            self.camera_manager.stop_camera()
        self.root.quit()
        self.root.destroy()

def main():
    """Run the MongoDB kiosk application"""
    app = MongoKioskApp()
    try:
        app.root.mainloop()
    except KeyboardInterrupt:
        app.quit_app()

if __name__ == "__main__":
    main()
