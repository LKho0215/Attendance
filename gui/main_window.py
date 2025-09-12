import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk
import threading
import time
from datetime import datetime

from core.database import DatabaseManager
from core.face_recognition import FaceRecognitionSystem, CameraManager
from core.barcode_scanner import BarcodeScanner
from core.attendance import AttendanceManager

# Set appearance mode and color theme
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class MainWindow:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Modern Attendance System")
        self.root.geometry("1200x800")
        
        # Initialize core components
        self.db = DatabaseManager()
        self.face_recognition = FaceRecognitionSystem()
        self.camera_manager = CameraManager()
        self.barcode_scanner = BarcodeScanner()
        self.attendance_manager = AttendanceManager(self.db)
        
        # GUI state variables
        self.camera_active = False
        self.recognition_mode = "face"  # "face" or "barcode"
        self.video_label = None
        self.attendance_tree = None
        
        # Create GUI
        self.create_widgets()
        
        # Load known faces (after GUI is created)
        self.load_known_faces()
        
        # Start GUI update loop
        self.update_gui()
    
    def create_widgets(self):
        """Create the main GUI components"""
        # Create main container
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create header
        self.create_header()
        
        # Create main content area
        self.create_main_content()
        
        # Create status bar
        self.create_status_bar()
    
    def create_header(self):
        """Create the header section"""
        header_frame = ctk.CTkFrame(self.main_container)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Title
        title_label = ctk.CTkLabel(
            header_frame, 
            text="Attendance Management System",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=15)
        
        # Current time
        self.time_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=14)
        )
        self.time_label.pack(side="right", padx=20, pady=15)
    
    def create_main_content(self):
        """Create the main content area"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create tabs
        self.create_attendance_tab()
        self.create_employee_tab()
        self.create_reports_tab()
    
    def create_attendance_tab(self):
        """Create the attendance tracking tab"""
        attendance_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(attendance_frame, text="Attendance")
        
        # Left panel - Controls
        left_panel = ctk.CTkFrame(attendance_frame)
        left_panel.pack(side="left", fill="y", padx=(10, 5), pady=10)
        
        # Mode selection
        mode_label = ctk.CTkLabel(left_panel, text="Recognition Mode", font=ctk.CTkFont(size=16, weight="bold"))
        mode_label.pack(pady=(20, 10))
        
        self.mode_var = ctk.StringVar(value="face")
        face_radio = ctk.CTkRadioButton(left_panel, text="Face Recognition", variable=self.mode_var, value="face")
        face_radio.pack(pady=5)
        
        barcode_radio = ctk.CTkRadioButton(left_panel, text="Barcode/QR Scanner", variable=self.mode_var, value="barcode")
        barcode_radio.pack(pady=5)
        
        # Camera controls
        camera_label = ctk.CTkLabel(left_panel, text="Camera Controls", font=ctk.CTkFont(size=16, weight="bold"))
        camera_label.pack(pady=(30, 10))
        
        self.start_camera_btn = ctk.CTkButton(
            left_panel, 
            text="Start Camera", 
            command=self.start_camera,
            width=200
        )
        self.start_camera_btn.pack(pady=5)
        
        self.stop_camera_btn = ctk.CTkButton(
            left_panel, 
            text="Stop Camera", 
            command=self.stop_camera,
            width=200,
            state="disabled"
        )
        self.stop_camera_btn.pack(pady=5)
        
        # Manual entry
        manual_label = ctk.CTkLabel(left_panel, text="Manual Entry", font=ctk.CTkFont(size=16, weight="bold"))
        manual_label.pack(pady=(30, 10))
        
        self.employee_id_entry = ctk.CTkEntry(left_panel, placeholder_text="Employee ID", width=200)
        self.employee_id_entry.pack(pady=5)
        
        manual_checkin_btn = ctk.CTkButton(
            left_panel, 
            text="Manual Check In", 
            command=self.manual_checkin,
            width=200
        )
        manual_checkin_btn.pack(pady=5)
        
        manual_checkout_btn = ctk.CTkButton(
            left_panel, 
            text="Manual Check Out", 
            command=self.manual_checkout,
            width=200
        )
        manual_checkout_btn.pack(pady=5)
        
        # Right panel - Video feed and attendance list
        right_panel = ctk.CTkFrame(attendance_frame)
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        
        # Video feed
        video_frame = ctk.CTkFrame(right_panel)
        video_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        video_label_header = ctk.CTkLabel(video_frame, text="Camera Feed", font=ctk.CTkFont(size=16, weight="bold"))
        video_label_header.pack(pady=(10, 5))
        
        self.video_label = tk.Label(video_frame, bg="black", width=640, height=480)
        self.video_label.pack(pady=(0, 10))
        
        # Today's attendance
        attendance_frame_widget = ctk.CTkFrame(right_panel)
        attendance_frame_widget.pack(fill="both", expand=True, padx=10, pady=5)
        
        attendance_label = ctk.CTkLabel(attendance_frame_widget, text="Today's Attendance", font=ctk.CTkFont(size=16, weight="bold"))
        attendance_label.pack(pady=(10, 5))
        
        # Create treeview for attendance
        columns = ("Employee ID", "Name", "Time", "Method", "Status")
        self.attendance_tree = ttk.Treeview(attendance_frame_widget, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.attendance_tree.heading(col, text=col)
            self.attendance_tree.column(col, width=120)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(attendance_frame_widget, orient="vertical", command=self.attendance_tree.yview)
        self.attendance_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        tree_frame = tk.Frame(attendance_frame_widget)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.attendance_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            attendance_frame_widget, 
            text="Refresh Attendance", 
            command=self.refresh_attendance
        )
        refresh_btn.pack(pady=(0, 10))
    
    def create_employee_tab(self):
        """Create the employee management tab"""
        employee_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(employee_frame, text="Employee Management")
        
        # Left panel - Add employee form
        left_panel = ctk.CTkFrame(employee_frame)
        left_panel.pack(side="left", fill="y", padx=(10, 5), pady=10)
        
        add_label = ctk.CTkLabel(left_panel, text="Add New Employee", font=ctk.CTkFont(size=16, weight="bold"))
        add_label.pack(pady=(20, 10))
        
        self.emp_id_entry = ctk.CTkEntry(left_panel, placeholder_text="Employee ID", width=250)
        self.emp_id_entry.pack(pady=5)
        
        self.emp_name_entry = ctk.CTkEntry(left_panel, placeholder_text="Full Name", width=250)
        self.emp_name_entry.pack(pady=5)
        
        self.emp_dept_entry = ctk.CTkEntry(left_panel, placeholder_text="Department", width=250)
        self.emp_dept_entry.pack(pady=5)
        
        # Face photo section
        photo_label = ctk.CTkLabel(left_panel, text="Employee Photo", font=ctk.CTkFont(size=14, weight="bold"))
        photo_label.pack(pady=(20, 10))
        
        self.photo_path_var = tk.StringVar()
        photo_btn = ctk.CTkButton(
            left_panel, 
            text="Select Photo", 
            command=self.select_employee_photo,
            width=250
        )
        photo_btn.pack(pady=5)
        
        capture_photo_btn = ctk.CTkButton(
            left_panel, 
            text="Capture from Camera", 
            command=self.capture_employee_photo,
            width=250
        )
        capture_photo_btn.pack(pady=5)
        
        add_employee_btn = ctk.CTkButton(
            left_panel, 
            text="Add Employee", 
            command=self.add_employee,
            width=250,
            fg_color="green"
        )
        add_employee_btn.pack(pady=20)
        
        # Right panel - Employee list
        right_panel = ctk.CTkFrame(employee_frame)
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        
        list_label = ctk.CTkLabel(right_panel, text="Employee List", font=ctk.CTkFont(size=16, weight="bold"))
        list_label.pack(pady=(10, 5))
        
        # Employee treeview
        emp_columns = ("Employee ID", "Name", "Department", "Has Face Data")
        self.employee_tree = ttk.Treeview(right_panel, columns=emp_columns, show="headings", height=15)
        
        for col in emp_columns:
            self.employee_tree.heading(col, text=col)
            self.employee_tree.column(col, width=150)
        
        # Employee scrollbar
        emp_scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=self.employee_tree.yview)
        self.employee_tree.configure(yscrollcommand=emp_scrollbar.set)
        
        # Pack employee treeview
        emp_tree_frame = tk.Frame(right_panel)
        emp_tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.employee_tree.pack(side="left", fill="both", expand=True)
        emp_scrollbar.pack(side="right", fill="y")
        
        # Employee management buttons
        btn_frame = ctk.CTkFrame(right_panel)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        refresh_emp_btn = ctk.CTkButton(btn_frame, text="Refresh List", command=self.refresh_employees)
        refresh_emp_btn.pack(side="left", padx=5, pady=10)
        
        delete_emp_btn = ctk.CTkButton(btn_frame, text="Delete Selected", command=self.delete_employee, fg_color="red")
        delete_emp_btn.pack(side="left", padx=5, pady=10)
    
    def create_reports_tab(self):
        """Create the reports and statistics tab"""
        reports_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(reports_frame, text="Reports & Statistics")
        
        # Summary cards
        summary_frame = ctk.CTkFrame(reports_frame)
        summary_frame.pack(fill="x", padx=10, pady=10)
        
        summary_label = ctk.CTkLabel(summary_frame, text="Today's Summary", font=ctk.CTkFont(size=18, weight="bold"))
        summary_label.pack(pady=(10, 5))
        
        # Statistics cards
        stats_frame = ctk.CTkFrame(summary_frame)
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        self.total_employees_label = ctk.CTkLabel(stats_frame, text="Total Employees: 0", font=ctk.CTkFont(size=14))
        self.total_employees_label.pack(side="left", padx=20, pady=10)
        
        self.present_today_label = ctk.CTkLabel(stats_frame, text="Present Today: 0", font=ctk.CTkFont(size=14))
        self.present_today_label.pack(side="left", padx=20, pady=10)
        
        self.attendance_rate_label = ctk.CTkLabel(stats_frame, text="Attendance Rate: 0%", font=ctk.CTkFont(size=14))
        self.attendance_rate_label.pack(side="left", padx=20, pady=10)
        
        # Report generation
        report_frame = ctk.CTkFrame(reports_frame)
        report_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        report_label = ctk.CTkLabel(report_frame, text="Generate Reports", font=ctk.CTkFont(size=16, weight="bold"))
        report_label.pack(pady=(10, 5))
        
        # Report buttons
        report_btn_frame = ctk.CTkFrame(report_frame)
        report_btn_frame.pack(pady=10)
        
        daily_report_btn = ctk.CTkButton(report_btn_frame, text="Daily Report", command=self.generate_daily_report)
        daily_report_btn.pack(side="left", padx=10, pady=10)
        
        weekly_report_btn = ctk.CTkButton(report_btn_frame, text="Weekly Report", command=self.generate_weekly_report)
        weekly_report_btn.pack(side="left", padx=10, pady=10)
        
        monthly_report_btn = ctk.CTkButton(report_btn_frame, text="Monthly Report", command=self.generate_monthly_report)
        monthly_report_btn.pack(side="left", padx=10, pady=10)
    
    def create_status_bar(self):
        """Create the status bar"""
        self.status_frame = ctk.CTkFrame(self.main_container)
        self.status_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="Ready", font=ctk.CTkFont(size=12))
        self.status_label.pack(side="left", padx=10, pady=5)
        
        self.camera_status_label = ctk.CTkLabel(self.status_frame, text="Camera: Inactive", font=ctk.CTkFont(size=12))
        self.camera_status_label.pack(side="right", padx=10, pady=5)
    
    def load_known_faces(self):
        """Load known faces from database"""
        employees_with_faces = self.db.get_all_face_images()
        self.face_recognition.load_known_faces(employees_with_faces)
        self.update_status(f"Loaded {len(employees_with_faces)} face images")
    
    def start_camera(self):
        """Start the camera for recognition"""
        if self.camera_manager.start_camera():
            self.camera_active = True
            self.start_camera_btn.configure(state="disabled")
            self.stop_camera_btn.configure(state="normal")
            self.camera_status_label.configure(text="Camera: Active")
            self.recognition_mode = self.mode_var.get()
            self.update_status(f"Camera started in {self.recognition_mode} mode")
        else:
            messagebox.showerror("Error", "Failed to start camera")
    
    def stop_camera(self):
        """Stop the camera"""
        self.camera_active = False
        self.camera_manager.stop_camera()
        self.start_camera_btn.configure(state="normal")
        self.stop_camera_btn.configure(state="disabled")
        self.camera_status_label.configure(text="Camera: Inactive")
        
        # Clear video display
        if self.video_label:
            self.video_label.configure(image="")
        
        self.update_status("Camera stopped")
    
    def process_camera_frame(self):
        """Process camera frame for recognition"""
        if not self.camera_active:
            return
        
        frame = self.camera_manager.get_frame()
        if frame is None:
            return
        
        # Process based on recognition mode
        if self.recognition_mode == "face":
            self.process_face_recognition(frame)
        else:
            self.process_barcode_scanning(frame)
    
    def process_face_recognition(self, frame):
        """Process frame for face recognition"""
        try:
            recognized_faces = self.face_recognition.process_video_frame(frame)
            
            # Draw face boxes
            frame_with_boxes = self.face_recognition.draw_face_boxes(frame, recognized_faces)
            
            # Check for recognized faces and record attendance
            for face in recognized_faces:
                if face['employee_id'] and face['name']:
                    # Auto-record attendance (you might want to add confirmation)
                    success, message = self.attendance_manager.toggle_attendance(
                        face['employee_id'], "face_recognition"
                    )
                    if success:
                        self.update_status(message)
                        self.refresh_attendance()
            
            # Display frame
            self.display_frame(frame_with_boxes)
            
        except Exception as e:
            print(f"Error in face recognition: {e}")
    
    def process_barcode_scanning(self, frame):
        """Process frame for barcode scanning"""
        try:
            valid_ids, all_codes = self.barcode_scanner.process_video_frame(frame)
            
            # Draw barcode boxes
            frame_with_boxes = self.barcode_scanner.draw_barcode_boxes(frame, all_codes)
            
            # Process valid employee IDs
            for code_data in valid_ids:
                employee_id = code_data['employee_id']
                success, message = self.attendance_manager.toggle_attendance(
                    employee_id, f"{code_data['type'].lower()}_scan"
                )
                if success:
                    self.update_status(message)
                    self.refresh_attendance()
            
            # Display frame
            self.display_frame(frame_with_boxes)
            
        except Exception as e:
            print(f"Error in barcode scanning: {e}")
    
    def display_frame(self, frame):
        """Display frame in the video label"""
        try:
            # Resize frame to fit display
            height, width = frame.shape[:2]
            max_width, max_height = 640, 480
            
            scale = min(max_width/width, max_height/height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            frame_resized = cv2.resize(frame, (new_width, new_height))
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image and then to PhotoImage
            image_pil = Image.fromarray(frame_rgb)
            image_tk = ImageTk.PhotoImage(image_pil)
            
            # Update video label
            if self.video_label:
                self.video_label.configure(image=image_tk)
                self.video_label.image = image_tk  # Keep a reference
                
        except Exception as e:
            print(f"Error displaying frame: {e}")
    
    def manual_checkin(self):
        """Manual check-in"""
        employee_id = self.employee_id_entry.get().strip()
        if not employee_id:
            messagebox.showwarning("Warning", "Please enter an employee ID")
            return
        
        success, message = self.attendance_manager.check_in_employee(employee_id, "manual")
        if success:
            messagebox.showinfo("Success", message)
            self.employee_id_entry.delete(0, "end")
            self.refresh_attendance()
        else:
            messagebox.showerror("Error", message)
    
    def manual_checkout(self):
        """Manual check-out"""
        employee_id = self.employee_id_entry.get().strip()
        if not employee_id:
            messagebox.showwarning("Warning", "Please enter an employee ID")
            return
        
        success, message = self.attendance_manager.check_out_employee(employee_id, "manual")
        if success:
            messagebox.showinfo("Success", message)
            self.employee_id_entry.delete(0, "end")
            self.refresh_attendance()
        else:
            messagebox.showerror("Error", message)
    
    def refresh_attendance(self):
        """Refresh the attendance list"""
        try:
            # Clear existing items
            for item in self.attendance_tree.get_children():
                self.attendance_tree.delete(item)
            
            # Get today's attendance
            attendance_records = self.db.get_attendance_today()
            
            # Insert new items
            for record in attendance_records:
                time_str = record['timestamp'].split('.')[0]  # Remove microseconds
                self.attendance_tree.insert("", "end", values=(
                    record['employee_id'],
                    record['name'],
                    time_str,
                    record['method'],
                    record['status'].upper()
                ))
            
            # Update statistics
            self.update_statistics()
            
        except Exception as e:
            print(f"Error refreshing attendance: {e}")
    
    def select_employee_photo(self):
        """Select employee photo from file"""
        file_path = filedialog.askopenfilename(
            title="Select Employee Photo",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if file_path:
            self.photo_path_var.set(file_path)
            self.update_status(f"Photo selected: {file_path}")
    
    def capture_employee_photo(self):
        """Capture employee photo from camera"""
        # This would open a camera capture dialog
        messagebox.showinfo("Info", "Camera capture feature - to be implemented")
    
    def add_employee(self):
        """Add new employee"""
        employee_id = self.emp_id_entry.get().strip()
        name = self.emp_name_entry.get().strip()
        department = self.emp_dept_entry.get().strip()
        
        if not employee_id or not name:
            messagebox.showwarning("Warning", "Employee ID and Name are required")
            return
        
        # Process face encoding if photo is provided
        face_encoding = None
        photo_path = self.photo_path_var.get()
        if photo_path:
            face_encoding = self.face_recognition.encode_face_from_image(photo_path)
            if face_encoding is None:
                messagebox.showwarning("Warning", "No face detected in the selected photo")
        
        # Add employee to database
        success = self.db.add_employee(employee_id, name, department, face_encoding)
        if success:
            messagebox.showinfo("Success", f"Employee {name} added successfully")
            
            # Clear form
            self.emp_id_entry.delete(0, "end")
            self.emp_name_entry.delete(0, "end")
            self.emp_dept_entry.delete(0, "end")
            self.photo_path_var.set("")
            
            # Refresh lists
            self.refresh_employees()
            self.load_known_faces()
        else:
            messagebox.showerror("Error", "Employee ID already exists")
    
    def refresh_employees(self):
        """Refresh the employee list"""
        try:
            # Clear existing items
            for item in self.employee_tree.get_children():
                self.employee_tree.delete(item)
            
            # Get all employees
            employees = self.db.get_all_employees()
            employees_with_faces = self.db.get_all_face_images()
            face_employee_ids = {emp['employee_id'] for emp in employees_with_faces}
            
            # Insert new items
            for employee in employees:
                has_face = "Yes" if employee['employee_id'] in face_employee_ids else "No"
                self.employee_tree.insert("", "end", values=(
                    employee['employee_id'],
                    employee['name'],
                    employee['department'] or "",
                    has_face
                ))
                
        except Exception as e:
            print(f"Error refreshing employees: {e}")
    
    def delete_employee(self):
        """Delete selected employee"""
        selected = self.employee_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an employee to delete")
            return
        
        item = self.employee_tree.item(selected[0])
        employee_id = item['values'][0]
        employee_name = item['values'][1]
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Deletion", 
            f"Are you sure you want to delete employee {employee_name} ({employee_id})?\n\nThis will also delete all their attendance records."
        )
        
        if result:
            success = self.db.delete_employee(employee_id)
            if success:
                messagebox.showinfo("Success", f"Employee {employee_name} deleted successfully")
                self.refresh_employees()
                self.load_known_faces()
            else:
                messagebox.showerror("Error", "Failed to delete employee")
    
    def update_statistics(self):
        """Update the statistics display"""
        try:
            # Get employee count
            all_employees = self.db.get_all_employees()
            total_employees = len(all_employees)
            
            # Get today's attendance summary
            attendance_summary = self.attendance_manager.get_attendance_summary_today()
            present_today = len([emp for emp in attendance_summary.values() if emp['status'] == 'in'])
            
            # Calculate attendance rate
            attendance_rate = (present_today / total_employees * 100) if total_employees > 0 else 0
            
            # Update labels
            self.total_employees_label.configure(text=f"Total Employees: {total_employees}")
            self.present_today_label.configure(text=f"Present Today: {present_today}")
            self.attendance_rate_label.configure(text=f"Attendance Rate: {attendance_rate:.1f}%")
            
        except Exception as e:
            print(f"Error updating statistics: {e}")
    
    def generate_daily_report(self):
        """Generate daily attendance report"""
        messagebox.showinfo("Info", "Daily report generation - to be implemented")
    
    def generate_weekly_report(self):
        """Generate weekly attendance report"""
        messagebox.showinfo("Info", "Weekly report generation - to be implemented")
    
    def generate_monthly_report(self):
        """Generate monthly attendance report"""
        messagebox.showinfo("Info", "Monthly report generation - to be implemented")
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_label.configure(text=message)
    
    def update_gui(self):
        """Main GUI update loop"""
        try:
            # Update time
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.configure(text=current_time)
            
            # Process camera frame if active
            if self.camera_active:
                self.process_camera_frame()
            
        except Exception as e:
            print(f"Error in GUI update: {e}")
        
        # Schedule next update
        self.root.after(100, self.update_gui)  # Update every 100ms
    
    def run(self):
        """Start the application"""
        # Initial data load
        self.refresh_attendance()
        self.refresh_employees()
        
        # Start main loop
        self.root.mainloop()
    
    def __del__(self):
        """Cleanup when application closes"""
        if hasattr(self, 'camera_manager'):
            self.camera_manager.stop_camera()
