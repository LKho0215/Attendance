import customtkinter as ctk
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
import threading
import time
import csv
import os
import ctypes
import re
import numpy as np
import traceback
import pygame
import time
from datetime import datetime, timedelta, time as dt_time

# Audio feedback imports
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
    print("[AUDIO] Pygame audio initialized successfully")
except ImportError:
    PYGAME_AVAILABLE = False
    print("[AUDIO] Pygame not available, falling back to system audio")

try:
    import winsound  # Windows built-in audio fallback
    WINSOUND_AVAILABLE = True
    print("[AUDIO] Windows winsound available as fallback")
except ImportError:
    WINSOUND_AVAILABLE = False
    print("[AUDIO] Winsound not available")

# Check if any audio is available
AUDIO_AVAILABLE = PYGAME_AVAILABLE or WINSOUND_AVAILABLE
print(f"[AUDIO] Audio system status - Pygame: {PYGAME_AVAILABLE}, Winsound: {WINSOUND_AVAILABLE}, Overall: {AUDIO_AVAILABLE}")

from core.mongodb_manager import MongoDBManager
from core.deepface_recognition import DeepFaceRecognitionSystem, CameraManager
from core.barcode_scanner import BarcodeScanner
from core.attendance import AttendanceManager
from core.mongo_location_manager import MongoLocationManager
from core.attendance_ultra_light import AttendanceUltraLightDetector

# Set appearance mode and color theme2
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Configuration constants
CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence required for face recognition

class SimpleKioskApp:
    def __init__(self):
        # Make application DPI-aware (must be done before creating tkinter window)
        try:
            import ctypes
            # Tell Windows this app is DPI-aware
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        self.root = ctk.CTk()
        self.root.title("Attendance Kiosk")
        
        # Kiosk mode settings
        self.setup_kiosk_mode()
        
        # Initialize core components
        try:
            self.db = MongoDBManager()
            self.attendance_manager = AttendanceManager(self.db)
            self.location_manager = MongoLocationManager(self.db)
            
        except Exception as e:
            print(f"[INIT ERROR] Failed to initialize MongoDB: {e}")
            messagebox.showerror("Database Error", 
                               f"Failed to connect to MongoDB:\n{e}\n\nPlease check your mongo_config.py file.")
            return
        
        # Face detection method configuration
        self.use_ultra_light_detection = True  # Set to True for ultra-fast detection, False for DeepFace
        
        if self.use_ultra_light_detection:
            # Initialize Ultra Light Face Detection for maximum performance
            print("[INIT DEBUG] Initializing Ultra Light Face Detection...")
            self.ultra_light_detector = AttendanceUltraLightDetector(confidence_threshold=0.7)
            print("[INIT DEBUG] Ultra Light Face Detection initialized")
            
            # Still keep face recognition for enrollment/verification if needed
            self.face_recognition = DeepFaceRecognitionSystem(detector_backend='mtcnn')
            print("[INIT DEBUG] DeepFace recognition system initialized (backup)")
        else:
            # Use traditional DeepFace system
            self.face_recognition = DeepFaceRecognitionSystem(detector_backend='mtcnn')
            print("[INIT DEBUG] DeepFace recognition system initialized")
            
            # Start background face processing
            self.face_recognition.start_background_processing()
            print("[INIT DEBUG] Background face processing started")
            
            self.ultra_light_detector = None
        
        self.camera_manager = CameraManager()
        print("[INIT DEBUG] Camera manager initialized")
        print("[INIT DEBUG] Camera manager initialized")
        
        self.barcode_scanner = BarcodeScanner()
        print("[INIT DEBUG] Barcode scanner initialized")
        
        # GUI state variables
        self.camera_active = False
        self.current_mode = "auto"  # auto, manual
        self.attendance_mode = "UNIFIED"  # Unified attendance system
        self.auto_timeout = 3  # seconds to show result
        self.last_history_update = 0  # for periodic updates
        
        # Camera management for registration
        self.main_camera_paused = False  # Flag to pause main camera during registration
        self.reg_camera_active = False  # Registration camera preview active
        self.reg_capture_active = False  # Registration capture process active
        
        # Face detection warm-up system
        self.face_warmup_enabled = True  # Enable/disable warm-up system
        self.face_warmup_frames = 15  # Number of consecutive frames required before recognition (increased from 3)
        self.face_warmup_stability_threshold = 0.08  # Maximum allowed face movement (reduced from 0.1 for more stability)
        self.face_detection_history = {}  # Track detected faces across frames
        self.frame_counter = 0  # Frame counter for tracking
        self.last_recognition_time = 0  # Prevent too frequent recognitions
        self.recognition_cooldown = 3.0  # Seconds between recognitions for same face (increased from 2.0)
        
        # Create GUI
        self.create_interface()
        
        # Initialize audio feedback
        self.audio_enabled = True  # Can be toggled via settings if needed
        print(f"[AUDIO] Audio feedback initialized: {AUDIO_AVAILABLE}")
        
        # Load shift settings from database (managed via web admin)
        self.load_shift_settings_from_db()
        
        # Start auto-refresh for shift settings (every 20 seconds)
        self.start_settings_auto_refresh(interval_seconds=20)

        # Set initial mode appearance
        # Initialize unified attendance system
        self.update_attendance_history()
        
        # Load known faces
        self.load_known_faces()
        
        # Start camera automatically on launch
        print("[INIT DEBUG] Starting camera automatically...")
        self.start_camera()
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Start update loop
        self.update_loop()
    
    def pause_camera_for_popup(self):
        """Pause camera when any popup appears"""
        if not self.main_camera_paused:
            print("[CAMERA DEBUG] Pausing camera for popup...")
            self.main_camera_paused = True
    
    def resume_camera_after_popup(self):
        """Resume camera after popup closes"""
        if self.main_camera_paused:
            print("[CAMERA DEBUG] Resuming camera after popup closed")
            self.main_camera_paused = False
    
    def setup_kiosk_mode(self):
        """Configure for kiosk operation"""
        # Get actual screen size (handling DPI scaling)
        try:
            import ctypes
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
        
        # Also show what tkinter thinks the screen size is
        tk_width = self.root.winfo_screenwidth()
        tk_height = self.root.winfo_screenheight()
        print(f"[KIOSK DEBUG] Tkinter detected dimensions: {tk_width}x{tk_height}")
        
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
        
        # Additional focus methods for better reliability
        self.root.lift()  # Bring window to front
        self.root.grab_set()  # Capture all events
        
        # Check final size after a moment
        self.root.after(100, self.check_final_size)
        
        # Schedule aggressive focus setting after UI is ready
        self.root.after(500, self.ensure_focus)
    
    def check_final_size(self):
        """Check and report the final window size"""
        final_width = self.root.winfo_width()
        final_height = self.root.winfo_height()
        print(f"[KIOSK DEBUG] Final window size: {final_width}x{final_height}")
        
        # Check if we're getting the full resolution
        if final_width >= 1920 and final_height >= 1080:
            print(f"[KIOSK DEBUG] ✓ Successfully achieved full 1920x1080 resolution")
        else:
            print(f"[KIOSK DEBUG] ⚠ Window size is smaller than expected 1920x1080")
            print(f"[KIOSK DEBUG] This might be due to DPI scaling or window decorations")
    
    def ensure_focus(self):
        """Ensure the application has focus and can receive keyboard input"""
        print("[FOCUS DEBUG] Ensuring application has focus...")
        try:
            # Step 1: Use Windows API to force the window to foreground
            self.force_window_to_foreground()
            
            # Step 2: Standard tkinter focus methods
            self.root.lift()                    # Bring to front
            self.root.attributes('-topmost', True)  # Stay on top
            self.root.focus_force()             # Force focus
            self.root.focus_set()               # Set focus
            
            # Step 3: Update to apply changes
            self.root.update()
            self.root.update_idletasks()
            
            # Step 4: Test keyboard focus
            self.root.bind('<KeyPress>', self.test_key_handler, add='+')
            
            print("[FOCUS DEBUG] ✓ Focus management completed")
            
            # Show visual indication that focus test is active
            self.status_label.configure(
                text="● PRESS ANY KEY to confirm keyboard focus is working",
                text_color="yellow"
            )
            
            # Schedule a focus check in a few seconds
            self.root.after(5000, self.check_focus_status)
            
        except Exception as e:
            print(f"[FOCUS DEBUG] ✗ Focus management failed: {e}")
    
    def force_window_to_foreground(self):
        """Use Windows API to force window to foreground"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Get the window handle
            hwnd = self.root.winfo_id()
            
            # Windows API functions
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # Get current foreground window and thread
            current_foreground = user32.GetForegroundWindow()
            current_thread = kernel32.GetCurrentThreadId()
            foreground_thread = user32.GetWindowThreadProcessId(current_foreground, None)
            
            # Attach to the foreground thread to gain focus rights
            if foreground_thread != current_thread:
                user32.AttachThreadInput(foreground_thread, current_thread, True)
                user32.SetForegroundWindow(hwnd)
                user32.AttachThreadInput(foreground_thread, current_thread, False)
            else:
                user32.SetForegroundWindow(hwnd)
            
            # Additional focus calls
            user32.SetActiveWindow(hwnd)
            user32.SetFocus(hwnd)
            user32.ShowWindow(hwnd, 1)  # SW_NORMAL
            user32.BringWindowToTop(hwnd)
            
            print("[FOCUS DEBUG] ✓ Windows API foreground focus applied")
            return True
            
        except Exception as e:
            print(f"[FOCUS DEBUG] Windows API focus failed: {e}")
            return False
    
    def test_key_handler(self, event):
        """Test handler to verify keyboard focus is working"""
        print(f"[FOCUS DEBUG] ✓ Keyboard focus confirmed - received key: {event.keysym}")
        # Update status to show focus is working
        self.status_label.configure(
            text="● FOCUS CONFIRMED - Keyboard input is working!",
            text_color="cyan"
        )
        # Remove the test handler after first key press
        self.root.unbind('<KeyPress>')
        # Return to normal status after 3 seconds
        self.root.after(3000, lambda: self.status_label.configure(
            text="● READY - Please position yourself in front of the camera",
            text_color="green"
        ))
    
    def check_focus_status(self):
        """Check and report current focus status"""
        try:
            focused_widget = self.root.focus_get()
            if focused_widget:
                print(f"[FOCUS DEBUG] ✓ Focus is on: {focused_widget}")
                # If we still have the test message, revert to normal
                if "PRESS ANY KEY" in self.status_label.cget("text"):
                    self.status_label.configure(
                        text="● READY - Please position yourself in front of the camera",
                        text_color="green"
                    )
                    print("[FOCUS DEBUG] No key pressed during test, but focus appears to be working")
            else:
                print("[FOCUS DEBUG] ⚠ No widget has focus - reapplying focus")
                self.root.focus_force()
                self.root.focus_set()
                self.status_label.configure(
                    text="● FOCUS ISSUE - Click on window if keyboard doesn't work",
                    text_color="orange"
                )
        except Exception as e:
            print(f"[FOCUS DEBUG] Focus check failed: {e}")
    
    def maintain_focus(self):
        """Periodic focus maintenance to ensure keyboard input works"""
        try:
            # Check if we still have focus
            focused_widget = self.root.focus_get()
            if not focused_widget or focused_widget != self.root:
                # We've lost focus, regain it
                print("[FOCUS DEBUG] Focus lost, regaining...")
                self.root.lift()
                self.root.focus_force()
                self.root.focus_set()
                
                # Try Windows API if available
                try:
                    import ctypes
                    hwnd = self.root.winfo_id()
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                except:
                    pass  # Not critical if this fails
                    
        except Exception as e:
            # Don't spam the console, just try to regain focus
            self.root.focus_force()
    
    def create_interface(self):
        """Create the main interface"""
        # Main container
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)
        
        # Header
        self.create_header()
        
        # Content area with camera and controls - reduced padding for more space
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=(5, 10))
        
        # Left side - Camera feed (smaller, fixed width)
        self.camera_frame = ctk.CTkFrame(self.content_frame, width=480, height=400)
        self.camera_frame.pack(side="left", fill="y", padx=(10, 20), pady=10)
        self.camera_frame.pack_propagate(False)  # Maintain fixed size
        
        self.camera_label = ctk.CTkLabel(
            self.camera_frame, 
            text="📷 Camera Off\n\nPress Numpad +\nto activate camera for recognition",
            font=ctk.CTkFont(size=20)
        )
        self.camera_label.pack(expand=True, padx=15, pady=15)
        
        # Group Check Toggle
        self.group_toggle_frame = ctk.CTkFrame(self.camera_frame)
        self.group_toggle_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        # Create a frame for the switch and label
        switch_container = ctk.CTkFrame(self.group_toggle_frame, fg_color="transparent")
        switch_container.pack(pady=10)
        
        # Label for the switch
        switch_label = ctk.CTkLabel(
            switch_container,
            text="👥 Group Check:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        switch_label.pack(side="left", padx=(0, 10))
        
        # Switch toggle
        self.group_check_var = ctk.BooleanVar(value=False)
        self.group_toggle = ctk.CTkSwitch(
            switch_container,
            text="",
            variable=self.group_check_var,
            command=self.toggle_group_mode,
            width=50,
            height=25
        )
        self.group_toggle.pack(side="left")
        
        # Group List Frame (initially hidden)
        self.group_list_frame = ctk.CTkFrame(self.camera_frame)
        
        # Scrollable group list
        self.group_scroll_frame = ctk.CTkScrollableFrame(
            self.group_list_frame,
            height=120,
        )
        self.group_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Group action buttons
        self.group_buttons_frame = ctk.CTkFrame(self.group_list_frame)
        self.group_buttons_frame.pack(fill="x", padx=10, pady=5)
        
        self.process_group_btn = ctk.CTkButton(
            self.group_buttons_frame,
            text="Check Out",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.process_group_checkout,
            fg_color="green",
            hover_color="darkgreen",
            height=35
        )
        self.process_group_btn.pack(side="left", padx=5, pady=5)
        
        self.clear_group_btn = ctk.CTkButton(
            self.group_buttons_frame,
            text="Clear List",
            font=ctk.CTkFont(size=12),
            command=self.clear_group_list,
            fg_color="red",
            hover_color="darkred",
            height=35
        )
        self.clear_group_btn.pack(side="right", padx=5, pady=5)
        
        # Initialize group data
        self.group_employees = []
        
        # Right side - Attendance history (larger, expandable)
        self.control_frame = ctk.CTkFrame(self.content_frame)
        self.control_frame.pack(side="right", fill="both", expand=True, padx=(20, 10), pady=10)
        
        self.create_controls()
        
        # Bottom - Status and messages
        self.create_status_area()
    
    def create_header(self):
        """Create header with time display only"""
        header_frame = ctk.CTkFrame(self.main_frame, height=60)
        header_frame.pack(fill="x", padx=20, pady=10)
        header_frame.pack_propagate(False)

        self.title_label = ctk.CTkLabel(
            header_frame,
            text="ATTENDANCE SYSTEM",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(side="left", padx=20, pady=15)
        
        self.time_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.time_label.pack(side="right", padx=20, pady=15)
    
    def create_controls(self):
        """Create unified attendance interface"""
        # Create the unified attendance interface directly
        self.create_unified_interface()
        
        # Load initial attendance data
        self.update_attendance_history()
    
    def create_unified_interface(self):
        """Create unified attendance interface for all types of attendance"""
        self.unified_interface = ctk.CTkFrame(self.control_frame)
        self.unified_interface.pack(fill="both", expand=True, padx=10, pady=10)
        
        
        # Unified attendance history - larger area for better visibility
        self.unified_history_frame = ctk.CTkScrollableFrame(
            self.unified_interface,
            width=600,
            height=700,
            fg_color=("gray95", "gray10"),
            border_width=2,
            border_color=("#8A2BE2", "#9370DB")  # BlueViolet and MediumSlateBlue
        )
        self.unified_history_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10)) 
        
    
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
        # Original shortcuts (for full keyboards)
        self.root.bind('<F4>', lambda e: self.toggle_kiosk_mode())          # F4 to toggle fullscreen
        self.root.bind('<Escape>', lambda e: self.clear_message())         # ESC to clear messages
        self.root.bind('<Alt-F4>', lambda e: self.quit_app())
        
        # Numpad shortcuts (for numpad-only setups)
        self.root.bind('<KP_Subtract>', lambda e: self.quit_app())          # Numpad -
        self.root.bind('<minus>', lambda e: self.quit_app())                # Regular -
        self.root.bind('<KP_Add>', lambda e: self.toggle_camera())          # Numpad + (toggle camera)
        self.root.bind('<plus>', lambda e: self.toggle_camera())            # Regular + (toggle camera)
        
        # Additional convenient shortcuts
        self.root.bind('<Return>', lambda e: self.show_manual_entry())      # Enter key - manual entry only
        self.root.bind('<KP_Enter>', lambda e: self.show_manual_entry())    # Numpad Enter
        
        # Focus on root to capture keys - use multiple methods for reliability
        self.root.focus_set()
        self.root.focus_force()
        
        # Make the window always stay on top and grab focus
        self.root.attributes('-topmost', True)
        self.root.lift()
    
    def toggle_kiosk_mode(self):
        """Toggle between fullscreen and windowed mode (for debugging)"""
        try:
            if self.root.attributes('-fullscreen'):
                # Switch to windowed mode
                self.root.attributes('-fullscreen', False)
                self.root.overrideredirect(False)
                self.root.geometry("1200x800+100+100")
                print("[KIOSK DEBUG] Switched to windowed mode")
            else:
                # Switch back to fullscreen
                self.setup_kiosk_mode()
                print("[KIOSK DEBUG] Switched back to fullscreen mode")
        except Exception as e:
            print(f"[KIOSK DEBUG] Toggle failed: {e}")
    
    def load_shift_settings_from_db(self):
        """Load shift settings from database (managed via web admin panel)"""
        try:
            # Try to load existing settings from database
            settings = self.db.get_admin_settings()
            if settings:
                # Load shift times from database
                self.early_shift_min_clockout = settings.get('early_shift_min_clockout', '17:00')  # 5:00 PM
                self.regular_shift_min_clockout = settings.get('regular_shift_min_clockout', '17:15')  # 5:15 PM
                
                # Face recognition warm-up settings
                self.face_warmup_enabled = settings.get('face_warmup_enabled', True)
                self.face_warmup_frames = settings.get('face_warmup_frames', 15)
                self.face_warmup_stability_threshold = settings.get('face_warmup_stability_threshold', 0.08)
                self.recognition_cooldown = settings.get('recognition_cooldown', 3.0)
                
                print(f"[SETTINGS] Loaded shift settings - Early: {self.early_shift_min_clockout}, Regular: {self.regular_shift_min_clockout}")
            else:
                # Set defaults if no settings found
                self.early_shift_min_clockout = '17:00'  # Early shift: 7:45 AM - 5:00 PM
                self.regular_shift_min_clockout = '17:15'  # Regular shift: 8:00 AM - 5:15 PM
                
                # Face recognition warm-up settings defaults
                self.face_warmup_enabled = True
                self.face_warmup_frames = 15
                self.face_warmup_stability_threshold = 0.08
                self.recognition_cooldown = 3.0
                
                print(f"[SETTINGS] Using default shift settings - Early: {self.early_shift_min_clockout}, Regular: {self.regular_shift_min_clockout}")
            
            # Update attendance manager with loaded settings
            self.update_attendance_manager_settings()
            
        except Exception as e:
            print(f"[SETTINGS] Error loading settings, using defaults: {e}")
            # Fallback defaults
            self.early_shift_min_clockout = '17:00'
            self.regular_shift_min_clockout = '17:15'
            
            # Face recognition warm-up settings defaults
            self.face_warmup_enabled = True
            self.face_warmup_frames = 15
            self.face_warmup_stability_threshold = 0.08
            self.recognition_cooldown = 3.0
            
            # Still try to update attendance manager
            self.update_attendance_manager_settings()
    
    def update_attendance_manager_settings(self):
        """Update the attendance manager with shift settings from database"""
        try:
            if hasattr(self.attendance_manager, 'update_shift_settings'):
                # New method that supports dual shift configuration
                self.attendance_manager.update_shift_settings(
                    early_shift_min_clockout=self.early_shift_min_clockout,
                    regular_shift_min_clockout=self.regular_shift_min_clockout
                )
                print(f"[SETTINGS] Updated attendance manager with shift settings - Early: {self.early_shift_min_clockout}, Regular: {self.regular_shift_min_clockout}")
            elif hasattr(self.attendance_manager, 'update_min_clock_out_time'):
                # Legacy support - use regular shift time as default
                self.attendance_manager.update_min_clock_out_time(self.regular_shift_min_clockout)
                print(f"[SETTINGS] Updated attendance manager with regular shift time (legacy): {self.regular_shift_min_clockout}")
            else:
                print("[SETTINGS] Attendance manager doesn't support settings update")
        except Exception as e:
            print(f"[SETTINGS] Error updating attendance manager: {e}")
    
    def start_settings_auto_refresh(self, interval_seconds=20):
        """Start automatic refresh of shift settings from database every X seconds"""
        def refresh_settings():
            try:
                print(f"[AUTO-REFRESH] Reloading shift settings from database...")
                self.load_shift_settings_from_db()
            except Exception as e:
                print(f"[AUTO-REFRESH] Error refreshing settings: {e}")
            finally:
                # Schedule next refresh
                self.root.after(interval_seconds * 1000, refresh_settings)
        
        # Start the first refresh cycle
        self.root.after(interval_seconds * 1000, refresh_settings)
        print(f"[AUTO-REFRESH] Settings auto-refresh enabled (every {interval_seconds} seconds)")
    
    def _check_face_distance_and_provide_feedback(self, frame, face_coords):
        if face_coords is None:
            return False, "Please position your face in the camera view"
        
        try:
            x, y, w, h = face_coords
            
            # Calculate face size relative to frame
            frame_area = frame.shape[0] * frame.shape[1]
            face_area = w * h
            face_ratio = face_area / frame_area
            
            # Define distance thresholds
            TOO_FAR_THRESHOLD = 0.03    # Less than 3% of frame
            TOO_NEAR_THRESHOLD = 0.4    # More than 40% of frame
            OPTIMAL_MIN = 0.08          # 8% for optimal range
            OPTIMAL_MAX = 0.25          # 25% for optimal range
            
            # Check distance and provide specific feedback
            if face_ratio < TOO_FAR_THRESHOLD:
                return False, "Please move CLOSER to the camera"
            elif face_ratio > TOO_NEAR_THRESHOLD:
                return False, "Please move FURTHER from the camera"
            elif face_ratio < OPTIMAL_MIN:
                return True, "Move a bit closer for optimal recognition"
            elif face_ratio > OPTIMAL_MAX:
                return True, "Move a bit further for optimal recognition"
            else:
                return True, "Perfect distance - ready for recognition"
                
        except Exception as e:
            print(f"[DISTANCE CHECK] Error checking distance: {e}")
            return False, "Error checking face distance"

    def _display_distance_feedback(self, display_frame, feedback_message, is_good_distance):
        try:
            # Choose color based on distance quality
            if is_good_distance:
                if "Perfect distance" in feedback_message:
                    color = (0, 255, 0)  # Green for perfect
                else:
                    color = (0, 255, 255)  # Yellow for acceptable
            else:
                color = (0, 0, 255)  # Red for bad distance
            
            # Display feedback at top of frame
            frame_height, frame_width = display_frame.shape[:2]
            
            # Background rectangle for better text visibility
            text_size = cv2.getTextSize(feedback_message, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            rect_width = text_size[0] + 20
            rect_height = text_size[1] + 20
            rect_x = (frame_width - rect_width) // 2
            rect_y = 20
            
            # Draw background rectangle
            cv2.rectangle(display_frame, 
                         (rect_x, rect_y), 
                         (rect_x + rect_width, rect_y + rect_height), 
                         (0, 0, 0), -1)
            
            # Draw text
            text_x = rect_x + 10
            text_y = rect_y + text_size[1] + 10
            cv2.putText(display_frame, feedback_message, 
                       (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
        except Exception as e:
            print(f"[DISPLAY FEEDBACK] Error displaying feedback: {e}")
    
    def update_unified_attendance_display(self):
        """Update the unified attendance display with all records"""
        self.update_attendance_history()
    
    def show_manual_entry(self):
        """Show unified manual entry dialog"""
        # Use the simple single-employee dialog for unified system
        self.show_simple_manual_entry()
    
    def show_simple_manual_entry(self):
        """Show simple manual entry dialog for CLOCK mode"""
        # Pause camera when popup appears
        self.pause_camera_for_popup()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Manual Entry")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (250 // 2)
        dialog.geometry(f"400x250+{x}+{y}")
        
        # Entry widgets
        tk.Label(dialog, text="Enter Employee ID:", font=("Arial", 16)).pack(pady=20)
        
        def validate_input(char, current_text):
            return char.isdigit() and len(current_text) <= 12
        
        vcmd = (dialog.register(validate_input), '%S', '%P')
        
        entry = tk.Entry(dialog, font=("Arial", 14), width=20, justify="center",
                        validate='key', validatecommand=vcmd)
        entry.pack(pady=10)
        entry.focus_set()
        
        def submit():
            nric = entry.get().strip()
            dialog.destroy()
            # Resume camera after popup closes
            self.resume_camera_after_popup()
            if nric and nric.isdigit():
                self.process_manual_entry(nric)
            elif nric:
                self.show_error_message("✗ NRIC must contain only numbers")
            else:
                self.show_error_message("✗ Please enter an NRIC")

        def cancel():
            dialog.destroy()
            # Resume camera after popup closes
            self.resume_camera_after_popup()
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Submit", font=("Arial", 12), 
                 command=submit, width=10).pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", font=("Arial", 12), 
                 command=cancel, width=10).pack(side="left", padx=10)
        
        # Bind Enter key
        entry.bind('<Return>', lambda e: submit())
        dialog.bind('<Escape>', lambda e: cancel())

    def process_manual_entry(self, nric):
        employee = self.db.get_employee(nric)
        if employee:
            success, message = self.process_attendance_with_location_check(nric, "manual")
            if success and message != "Location selection initiated":
                self.show_success_message(f"✓ {employee['name']} - {message}")
            elif not success:
                # Check if this is an early clock-out error
                if self.is_early_clockout_error(message):
                    self.handle_early_clockout_error(employee['name'], message)
                else:
                    self.show_error_message(f"✗ {message}")
            # If message is "Location selection initiated", the location dialog will handle the UI
        else:
            self.show_employee_not_found_dialog(nric)

    def process_attendance_with_location_check(self, nric, method):
        """Process unified attendance with smart logic for clock/check operations"""
        employee = self.db.get_employee(nric)
        if not employee:
            return False, f"Employee {nric} not found"

        # Check if group mode is enabled
        if hasattr(self, 'group_check_var') and self.group_check_var.get():
            # Group mode is ON - add to group list instead of processing immediately
            employee_name = employee['name']
            
            # Get today's attendance records
            today_records = self.attendance_manager.get_employee_attendance_today(nric)
            clock_records = [r for r in today_records if r.get('attendance_type') == 'clock']
            clock_records.sort(key=lambda x: x['timestamp'], reverse=True)
            last_clock_record = clock_records[0] if clock_records else None
            
            # Check if employee has clocked in today
            if not last_clock_record:
                self.show_group_error_notification(employee_name, nric, 'not_clocked_in')
                return False, f"{employee_name} has not clocked in yet today"
            
            # Check if employee has already clocked out (final clock out)
            if last_clock_record['status'] == 'out':
                self.show_group_error_notification(employee_name, nric, 'final_clock_out')
                return False, f"{employee_name} has already clocked out for the day"
            
            # Check if employee is already checked out (can't add to group if already checked out)
            check_records = [r for r in today_records if r.get('attendance_type') == 'check']
            check_records.sort(key=lambda x: x['timestamp'], reverse=True)
            last_check_record = check_records[0] if check_records else None
            
            if last_check_record and last_check_record['status'] == 'out':
                self.show_group_error_notification(employee_name, nric, 'already_checked_out')
                return False, f"{employee_name} is already checked out"
            
            # Validate that employee is within the allowed time window for check operations
            current_time = self.attendance_manager.get_current_time()
            current_time_only = current_time.time()
            
            # Get employee role and clock-in time to determine shift
            employee_role = employee.get('role', 'Staff')
            clock_in_time = datetime.fromisoformat(last_clock_record['timestamp']).time()
            
            # Determine if current time is within check operation window
            is_within_check_window = False
            
            if employee_role == 'Security':
                # Security: Same logic as clock-out time determination
                if clock_in_time >= dt_time(18, 0):  # Night shift
                    if current_time_only < dt_time(7, 0):  # Next day morning
                        is_within_check_window = False  # Can clock out now
                    elif current_time_only >= dt_time(18, 0):  # Same day, still in night shift
                        is_within_check_window = True  # Can check in/out
                    else:  # Same day, after 7 AM but before 6 PM
                        is_within_check_window = False  # Should have clocked out
                else:  # Day shift
                    is_within_check_window = current_time_only < dt_time(19, 0)  # Before 7:00 PM
            else:
                # Staff: Must be within the check window (after clock in, before minimum clock out time)
                # Check window ends when they're allowed to do final clock out
                if clock_in_time < dt_time(8, 0):  # Early shift
                    early_hour, early_minute = map(int, self.early_shift_min_clockout.split(':'))
                    final_clockout_time = dt_time(early_hour, early_minute)
                    is_within_check_window = current_time_only < final_clockout_time
                else:  # Regular shift
                    regular_hour, regular_minute = map(int, self.regular_shift_min_clockout.split(':'))
                    final_clockout_time = dt_time(regular_hour, regular_minute)
                    is_within_check_window = current_time_only < final_clockout_time
            
            if not is_within_check_window:
                if employee_role == 'Security':
                    if clock_in_time >= dt_time(18, 0):  # Night shift
                        min_clockout = "7:00 AM"
                        shift_type = "Night Shift"
                    else:  # Day shift
                        min_clockout = "7:00 PM"
                        shift_type = "Day Shift"
                else:
                    shift_type = "Early" if clock_in_time < dt_time(8, 0) else "Regular"
                    min_clockout = self.early_shift_min_clockout if shift_type == "Early" else self.regular_shift_min_clockout
                
                additional_info = f"Current time: {current_time_only.strftime('%I:%M %p')}\nMinimum clock-out: {min_clockout}"
                self.show_group_error_notification(employee_name, nric, 'not_in_check_window', additional_info)
                return False, f"{employee_name} can only do final clock out now (after {min_clockout}), not check out"
            
            # Add to group list
            if self.add_employee_to_group(nric, employee_name):
                return True, f"{employee_name} added to group list"
            else:
                self.show_group_error_notification(employee_name, nric, 'already_in_group')
                return False, f"{employee_name} is already in group list"
        
        # Normal mode - continue with regular processing
        
        # Get today's attendance records to determine what action to take
        today_records = self.attendance_manager.get_employee_attendance_today(nric)
        clock_records = [r for r in today_records if r.get('attendance_type') == 'clock']
        clock_records.sort(key=lambda x: x['timestamp'], reverse=True)
        last_clock_record = clock_records[0] if clock_records else None
        check_records = [r for r in today_records if r.get('attendance_type') == 'check']
        check_records.sort(key=lambda x: x['timestamp'], reverse=True)
        last_check_record = check_records[0] if check_records else None

        attendance_type = None
        status = None
        current_time = self.attendance_manager.get_current_time()
        current_time_only = current_time.time()
        employee_role = employee.get('role', 'Staff') if employee else 'Staff'

        # --- Security Special Logic - Check for Previous Day Night Shift ---
        if employee_role == 'Security':
            # Always check for previous day night shift first (regardless of today's records)
            prev_date = (current_time - timedelta(days=1)).date()
            prev_records = self.db.get_attendance_by_date(nric, prev_date)
            prev_clock_ins = [r for r in prev_records if r.get('attendance_type') == 'clock' and r['status'] == 'in']
            prev_clock_outs = [r for r in prev_records if r.get('attendance_type') == 'clock' and r['status'] == 'out']
            
            # Check if there was a night shift clock-in yesterday without clock-out
            night_shift_in = None
            for r in prev_clock_ins:
                t = datetime.fromisoformat(r['timestamp']).time()
                if t >= dt_time(18, 0):  # Night shift clock-in (6:00 PM or later)
                    night_shift_in = r
                    break
            
            # If there's an unfinished night shift from previous day, force clock-out
            if night_shift_in and not prev_clock_outs:
                if current_time_only >= dt_time(7, 0):
                    # Force clock-out for previous night shift - handle directly
                    employee = self.db.get_employee(nric)
                    current_time = self.attendance_manager.get_current_time()
                    
                    # Calculate overtime for night shift
                    min_clock_out_time = dt_time(7, 0)
                    total_seconds = (current_time_only.hour * 3600 + current_time_only.minute * 60) - (7 * 3600)
                    if total_seconds > 0:
                        overtime_hours = max(0, int(total_seconds / 3600))
                    else:
                        overtime_hours = 0
                    
                    # Record clock-out for previous day night shift
                    record_id = self.db.record_attendance(nric, method, "out", "clock", current_time, overtime_hours=overtime_hours)
                    
                    if record_id:
                        base_message = f"{employee['name']} (Security) clocked out from Night Shift (7:00 PM - 7:00 AM)"
                        if overtime_hours > 0:
                            base_message += f" - OT {overtime_hours} hour{'s' if overtime_hours > 1 else ''}"
                        return True, base_message
                    else:
                        return False, "Failed to record night shift clock-out"
                else:
                    return False, f"Night shift clock-out not allowed before 7:00 AM"
            
            # No previous night shift to complete - proceed with normal logic
            if not last_clock_record:
                # No clock record today - this is a new clock-in
                if dt_time(6, 0) <= current_time_only < dt_time(12, 0):
                    late = current_time_only > dt_time(7, 0)
                    shift_name = "Day Shift"
                elif dt_time(18, 0) <= current_time_only <= dt_time(23, 59) or dt_time(0, 0) <= current_time_only < dt_time(1, 0):
                    late = current_time_only > dt_time(19, 0)
                    shift_name = "Night Shift"
                else:
                    late = False
                    shift_name = "Security Shift"
                
                success, message = self.attendance_manager.process_attendance(
                    nric, method, "clock", None, is_late=late, shift_name=shift_name
                )
                return success, message

        # --- Universal Logic for Staff and Security ---
        # Alternating action logic for staff
        if not last_clock_record:
            attendance_type = "clock"
            status = "in"
        elif last_clock_record['status'] == 'in':
            # Already clocked in - determine if this should be check in/out or final clock out
            # Check current time to see if it's appropriate for clock out
            clock_in_time = datetime.fromisoformat(last_clock_record['timestamp']).time()
            is_clock_out_time = False
            
            if employee_role == 'Security':
                # Security: Check against expected shift end times
                if clock_in_time >= dt_time(18, 0):  # Night shift (6:00 PM - 7:00 AM next day)
                    # Night shift can clock out at 7:00 AM next day
                    # If it's same day and before midnight, not time to clock out yet
                    if current_time_only < dt_time(7, 0):  # Next day morning
                        is_clock_out_time = True
                    elif current_time_only >= dt_time(18, 0):  # Same day, still in night shift
                        is_clock_out_time = False
                    else:  # Same day, after 7 AM but before 6 PM - should have clocked out already
                        is_clock_out_time = True
                else:  # Day shift (6:00 AM - 7:00 PM same day)
                    # Day shift can clock out at 7:00 PM
                    is_clock_out_time = current_time_only >= dt_time(19, 0)  # 7:00 PM
            else:
                # Staff: Original logic
                if clock_in_time < dt_time(8, 0):
                    early_hour, early_minute = map(int, self.early_shift_min_clockout.split(':'))
                    min_clock_out = dt_time(early_hour, early_minute)
                    is_clock_out_time = current_time_only >= min_clock_out
                else:
                    regular_hour, regular_minute = map(int, self.regular_shift_min_clockout.split(':'))
                    min_clock_out = dt_time(regular_hour, regular_minute)
                    is_clock_out_time = current_time_only >= min_clock_out
            if is_clock_out_time:
                attendance_type = "clock"
                status = "out"
            else:
                if not last_check_record:
                    attendance_type = "check"
                    status = "out"
                else:
                    attendance_type = "check"
                    status = "in" if last_check_record['status'] == 'out' else "out"
        else:
            attendance_type = "clock"
            status = "in"

        # Handle location selection for check out operations
        if attendance_type == "check" and status == "out":
            self.handle_checkout_with_location_first_unified(nric, method)
            return True, "Location selection initiated"

        # Process normal attendance (clock in/out, check in)
        success, message = self.attendance_manager.process_attendance(
            nric, method, attendance_type, None
        )
        return success, message
    
    def handle_checkout_with_location_first_unified(self, nric, method):
        """Handle checkout by showing location selection first, then recording attendance for unified system"""
        
        # Pause camera to prevent continuous face recognition during location selection
        self.pause_camera_for_popup()
        
        def on_location_selected(location):
            # Resume camera after location selection (always, whether location selected or cancelled)
            self.resume_camera_after_popup()
            
            if location:
                # Check if this is an emergency clock-out
                is_emergency = location.get('emergency_clockout', False)
                emergency_reason = location.get('emergency_reason', '')
                
                if is_emergency:
                    # EMERGENCY CLOCK-OUT: Bypass time restrictions and force clock out
                    print(f"[EMERGENCY DEBUG] Processing emergency clock-out for {nric}")
                    print(f"[EMERGENCY DEBUG] Location: {location.get('name')}, Reason: {emergency_reason}")
                    
                    # Process emergency clock-out with override flag
                    success, message = self.attendance_manager.process_attendance(
                        nric, method, "clock", None, emergency_override=True
                    )
                    
                    if success:
                        # Get the attendance record ID from the message or query latest record
                        employee = self.db.get_employee(nric)
                        today_records = self.attendance_manager.get_employee_attendance_today(nric)
                        
                        # Get the most recent clock record
                        clock_records = [r for r in today_records if r.get('attendance_type') == 'clock']
                        if clock_records:
                            clock_records.sort(key=lambda x: x['timestamp'], reverse=True)
                            latest_record = clock_records[0]
                            record_id = latest_record.get('_id')
                            
                            # Update record with emergency information
                            location_data = {
                                "location_name": location.get('name', ''),
                                "address": location.get('address', ''),
                                "emergency_clockout": True,
                                "emergency_reason": emergency_reason
                            }
                            
                            self.db.update_attendance_location(record_id, location_data)
                            
                            location_name = location.get('name', 'Emergency location')
                            self.show_success_message(
                                f"🚨 {employee['name']} - EMERGENCY CLOCK-OUT\n📍 Going to: {location_name}\n⚠️ Reason: {emergency_reason[:50]}..."
                            )
                        else:
                            self.show_success_message(f"🚨 {employee['name']} - EMERGENCY CLOCK-OUT\n{message}")
                    else:
                        self.show_error_message(f"✗ Emergency clock-out failed: {message}")
                    
                    self.update_attendance_history()
                    return
                
                # Normal check-out with location
                current_time = self.attendance_manager.get_current_time()
                record_id = self.db.record_attendance(nric, method, "out", "check", current_time)
                
                if record_id:
                    # Prepare location data for attendance record
                    location_data = {
                        "location_name": location.get('name', ''),
                        "address": location.get('address', ''),
                        "type": location.get('type', 'work')  # Include checkout type
                    }
                    
                    # Update the attendance record with location information
                    success = self.db.update_attendance_location(record_id, location_data)
                    
                    if success:
                        employee = self.db.get_employee(nric)
                        location_name = location.get('name', 'Selected location')
                        self.show_success_message(
                            f"✓ {employee['name']} checked out\n📍 Going to: {location_name}"
                        )
                    else:
                        self.show_error_message("✗ Failed to save location")
                    
                    # Update the attendance display
                    self.update_attendance_history()
                else:
                    self.show_error_message("✗ Failed to record attendance")
            else:
                # User cancelled location selection - do NOT process checkout
                print("[LOCATION DEBUG] User cancelled location selection - checkout cancelled")
        
        # Open location selector dialog
        from core.location_selector import LocationSelector
        LocationSelector(
            parent=self.root,
            nric=nric,
            callback=on_location_selected
        )
    
    def handle_checkout_location_selection(self, attendance_id, nric):
        """Handle location selection for check-out (legacy method for existing attendance records)"""
        # Pause camera to prevent continuous face recognition during location selection
        self.pause_camera_for_popup()
        
        def on_location_selected(location):
            # Resume camera after location selection (always, whether location selected or cancelled)
            self.resume_camera_after_popup()
            
            if location:
                # Prepare location data for attendance record
                location_data = {
                    "location_name": location.get('name', ''),
                    "address": location.get('address', '')
                }
                
                # Update the attendance record with location information
                success = self.db.update_attendance_location(attendance_id, location_data)
                
                if success:
                    # Also save to location manager for favorites/history (optional)
                    self.location_manager.save_checkout_location(
                        attendance_id, nric, location
                    )
                    
                    employee = self.db.get_employee(nric)
                    location_name = location.get('name', 'Selected location')
                    self.show_success_message(
                        f"✓ {employee['name']} checked out\n📍 Going to: {location_name}"
                    )
                else:
                    self.show_error_message("✗ Failed to save location")
            else:
                # User cancelled location selection - that's okay, checkout is still recorded
                employee = self.db.get_employee(nric)
                self.show_success_message(f"✓ {employee['name']} checked out")
        
        # Open location selector dialog
        from core.location_selector import LocationSelector
        LocationSelector(
            parent=self.root,
            nric=nric,
            callback=on_location_selected
        )
    
    def show_employee_not_found_dialog(self, nric):
        """Show a dedicated error dialog for employee not found"""
        # Pause camera when popup appears
        self.pause_camera_for_popup()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Employee Not Found")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"350x200+{x}+{y}")
        
        # Configure dialog background
        dialog.configure(bg='#ff4444')
        
        # Error icon and message
        main_frame = tk.Frame(dialog, bg='#ff4444')
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Error icon
        tk.Label(main_frame, text="❌", font=("Arial", 32), 
                bg='#ff4444', fg='white').pack(pady=10)
        
        # Error message
        tk.Label(main_frame, text="EMPLOYEE NOT FOUND", 
                font=("Arial", 14, "bold"), bg='#ff4444', fg='white').pack()
        
        tk.Label(main_frame, text=f"Employee ID: {nric}", 
                font=("Arial", 12), bg='#ff4444', fg='white').pack(pady=5)
        
        tk.Label(main_frame, text="Please check the ID and try again", 
                font=("Arial", 10), bg='#ff4444', fg='white').pack(pady=5)
        
        # Close function to resume camera
        def close_dialog():
            dialog.destroy()
            self.resume_camera_after_popup()
        
        # OK button
        ok_button = tk.Button(main_frame, text="OK", font=("Arial", 12, "bold"),
                             command=close_dialog, width=10,
                             bg='white', fg='#ff4444', relief='raised', bd=2)
        ok_button.pack(pady=15)
        ok_button.focus_set()
        
        # Bind Enter and Escape keys
        dialog.bind('<Return>', lambda e: close_dialog())
        dialog.bind('<Escape>', lambda e: close_dialog())
        
        # Auto-close after 5 seconds
        dialog.after(5000, close_dialog)
    
    def show_already_checked_out_dialog(self, employee_name, nric):
        """Show error dialog for employee already checked out"""
        # Pause camera when popup appears
        self.pause_camera_for_popup()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Already Checked Out")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"350x200+{x}+{y}")
        
        # Configure dialog background
        dialog.configure(bg='#ff8800')
        
        # Warning icon and message
        main_frame = tk.Frame(dialog, bg='#ff8800')
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Warning icon
        tk.Label(main_frame, text="⚠️", font=("Arial", 32), 
                bg='#ff8800', fg='white').pack(pady=10)
        
        # Warning message
        tk.Label(main_frame, text="ALREADY CHECKED OUT", 
                font=("Arial", 14, "bold"), bg='#ff8800', fg='white').pack()
        
        tk.Label(main_frame, text=f"{employee_name} (ID: {nric})", 
                font=("Arial", 12), bg='#ff8800', fg='white').pack(pady=5)
        
        tk.Label(main_frame, text="Employee is already in checked out status", 
                font=("Arial", 10), bg='#ff8800', fg='white').pack(pady=5)
        
        # Close function to resume camera
        def close_dialog():
            dialog.destroy()
            self.resume_camera_after_popup()
        
        # OK button
        ok_button = tk.Button(main_frame, text="OK", font=("Arial", 12, "bold"),
                             command=close_dialog, width=10,
                             bg='white', fg='#ff8800', relief='raised', bd=2)
        ok_button.pack(pady=15)
        ok_button.focus_set()
        
        # Bind Enter and Escape keys
        dialog.bind('<Return>', lambda e: close_dialog())
        dialog.bind('<Escape>', lambda e: close_dialog())
        
        # Auto-close after 5 seconds
        dialog.after(5000, close_dialog)
    
    def show_group_error_notification(self, employee_name, nric, error_type, additional_info=""):
        """Show detailed error notification for group check scenarios"""
        # Define error configurations
        error_configs = {
            'not_clocked_in': {
                'title': 'Cannot Add to Group',
                'header': 'NOT CLOCKED IN',
                'icon': '❌',
                'bg_color': '#ff4444',
                'description': 'Employee has not clocked in today'
            },
            'already_checked_out': {
                'title': 'Cannot Add to Group', 
                'header': 'ALREADY CHECKED OUT',
                'icon': '⚠️',
                'bg_color': '#ff8800',
                'description': 'Employee is already in checked out status'
            },
            'not_in_check_window': {
                'title': 'Cannot Add to Group',
                'header': 'OUTSIDE CHECK WINDOW',
                'icon': '🕐',
                'bg_color': '#ff6600',
                'description': 'Current time is outside the allowed check window'
            },
            'already_in_group': {
                'title': 'Cannot Add to Group',
                'header': 'ALREADY IN GROUP',
                'icon': '✅',
                'bg_color': '#3399ff',
                'description': 'Employee is already added to the group list'
            },
            'final_clock_out': {
                'title': 'Cannot Add to Group',
                'header': 'ALREADY CLOCKED OUT',
                'icon': '🔒',
                'bg_color': '#666666',
                'description': 'Employee has completed final clock out for today'
            }
        }
        
        config = error_configs.get(error_type, error_configs['not_clocked_in'])
        
        # Pause camera when popup appears
        self.pause_camera_for_popup()
        
        dialog = tk.Toplevel(self.root)
        dialog.title(config['title'])
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (250 // 2)
        dialog.geometry(f"400x250+{x}+{y}")
        
        # Configure dialog background
        dialog.configure(bg=config['bg_color'])
        
        # Main frame
        main_frame = tk.Frame(dialog, bg=config['bg_color'])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Icon
        tk.Label(main_frame, text=config['icon'], font=("Arial", 36), 
                bg=config['bg_color'], fg='white').pack(pady=10)
        
        # Header message
        tk.Label(main_frame, text=config['header'], 
                font=("Arial", 14, "bold"), bg=config['bg_color'], fg='white').pack()
        
        # Employee info
        tk.Label(main_frame, text=f"{employee_name}", 
                font=("Arial", 13, "bold"), bg=config['bg_color'], fg='white').pack(pady=5)
        
        tk.Label(main_frame, text=f"ID: {nric}", 
                font=("Arial", 12), bg=config['bg_color'], fg='white').pack()
        
        # Description
        tk.Label(main_frame, text=config['description'], 
                font=("Arial", 11), bg=config['bg_color'], fg='white').pack(pady=10)
        
        # Additional info if provided
        if additional_info:
            tk.Label(main_frame, text=additional_info, 
                    font=("Arial", 10), bg=config['bg_color'], fg='white').pack(pady=5)
        
        # Close function to resume camera
        def close_dialog():
            dialog.destroy()
            self.resume_camera_after_popup()
        
        # OK button
        ok_button = tk.Button(main_frame, text="OK", font=("Arial", 12, "bold"),
                             command=close_dialog, width=10,
                             bg='white', fg=config['bg_color'], relief='raised', bd=2)
        ok_button.pack(pady=15)
        ok_button.focus_set()
        
        # Bind Enter and Escape keys
        dialog.bind('<Return>', lambda e: close_dialog())
        dialog.bind('<Escape>', lambda e: close_dialog())
        
        # Auto-close after 5 seconds
        dialog.after(5000, close_dialog)
    

    

    
    def show_temp_message(self, message, color, parent_dialog=None):

        if parent_dialog is not None:
            try:
                parent_dialog.destroy()
            except:
                pass
    
        """Show a temporary message dialog"""
        # Pause camera when popup appears
        self.pause_camera_for_popup()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Information")
        dialog.geometry("350x180")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (dialog.winfo_screenheight() // 2) - (180 // 2)
        dialog.geometry(f"350x180+{x}+{y}")
        
        # Configure dialog background based on color
        bg_color = '#ff8800' if color == 'orange' else '#ff4444'
        dialog.configure(bg=bg_color)
        
        # Message frame
        main_frame = tk.Frame(dialog, bg=bg_color)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Icon based on color
        icon = "⚠️" if color == 'orange' else "❌"
        tk.Label(main_frame, text=icon, font=("Arial", 32), 
                bg=bg_color, fg='white').pack(pady=10)
        
        # Message
        tk.Label(main_frame, text=message, 
                font=("Arial", 12, "bold"), bg=bg_color, fg='white').pack(pady=5)
        
        # Close function to resume camera
        def close_dialog():
            dialog.destroy()
            self.resume_camera_after_popup()
        
        # OK button
        ok_button = tk.Button(main_frame, text="OK", font=("Arial", 12, "bold"),
                             command=close_dialog, width=10,
                             bg='white', fg=bg_color, relief='raised', bd=2)
        ok_button.pack(pady=15)
        ok_button.focus_set()
        
        # Bind Enter and Escape keys
        dialog.bind('<Return>', lambda e: close_dialog())
        dialog.bind('<Escape>', lambda e: close_dialog())

        dialog.focus_set()
        
        # Auto-close after 3 seconds
        dialog.after(3000, close_dialog)
    

    
    # DEPRECATED: QR codes now process directly without confirmation
    # def show_qr_recognition_confirmation(self, qr_code, employee):
    #     """Show confirmation dialog for QR code recognition"""
    #     # This function is no longer used - QR codes are processed directly
    #     # since they are unique identifiers with high reliability
    #     pass

    def show_face_recognition_confirmation(self, face, employee):
        """Show confirmation dialog for face recognition"""
        try:
            print(f"[CONFIRMATION DEBUG] Starting face confirmation dialog for {employee['name']}")
            
            # Play detection beep when face is recognized
            self.play_scan_detected_beep()
            
            # Turn OFF camera after recognition (manual mode)
            self.stop_camera()
            print(f"[CONFIRMATION DEBUG] Camera turned OFF after face recognition")
            
            # Create custom dialog for larger size and font
            dialog = tk.Toplevel(self.root)
            dialog.title("Confirm Face Recognition")
            dialog.transient(self.root)  # Set to be on top of main window
            dialog.grab_set()  # Modal dialog
            
            # Make dialog larger
            dialog_width = 600
            dialog_height = 500
            dialog.geometry(f"{dialog_width}x{dialog_height}")
            dialog.resizable(True, True)
            
            # Center the dialog on screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
            dialog.geometry(f"+{x}+{y}")
            
            # Configure font sizes
            text_font = ("Arial", 14)
            button_font = ("Arial", 12, "bold")
            
            # Create dialog content
            employee_role = employee.get('roles', [])
            role_icon = '🛡️' if employee_role == 'Security' else '👥'
            confidence = face.get('confidence', 0.0) * 100
            
            # Main frame with padding
            main_frame = tk.Frame(dialog, padx=20, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Recognition details in a frame
            details_frame = tk.Frame(main_frame)
            details_frame.pack(fill=tk.BOTH, expand=True, pady=20)
            
            # Employee details with larger font
            details_text = f"Recognized: {face['name']}\n\n"
            details_text += f"Employee ID: {face['nric']}\n\n"
            details_text += f"Role: {role_icon} {employee_role}\n\n"
            details_text += f"Confidence: {confidence:.2f}%"
            
            details_label = tk.Label(
                details_frame,
                text=details_text,
                font=text_font,
                justify=tk.LEFT,
                pady=20
            )
            details_label.pack()
            
            # Question
            question_label = tk.Label(
                main_frame,
                text="Is this recognition correct?",
                font=text_font,
                fg="#e74c3c",
                pady=10
            )
            question_label.pack()
            
            # Button frame
            button_frame = tk.Frame(main_frame)
            button_frame.pack(pady=20)
            
            # Store the result
            self.confirmation_result = None
            
            def on_yes():
                self.confirmation_result = True
                dialog.destroy()
                
            def on_no():
                self.confirmation_result = False
                dialog.destroy()
            
            # Yes button (green)
            yes_button = tk.Button(
                button_frame,
                text="✓ YES - Correct",
                font=button_font,
                bg="#27ae60",
                fg="white",
                padx=30,
                pady=10,
                command=on_yes
            )
            yes_button.pack(side=tk.LEFT, padx=20)
            
            # No button (red)
            no_button = tk.Button(
                button_frame,
                text="✗ NO - Try Again",
                font=button_font,
                bg="#e74c3c",
                fg="white",
                padx=30,
                pady=10,
                command=on_no
            )
            no_button.pack(side=tk.LEFT, padx=20)
            
            # Make buttons focusable and bind Enter/Escape keys
            yes_button.focus_set()
            dialog.bind('<Return>', lambda e: on_yes())
            dialog.bind('<Escape>', lambda e: on_no())
            
            # Wait for dialog to close
            self.root.wait_window(dialog)
            
            # Process result after dialog closes
            result = self.confirmation_result
            print(f"[CONFIRMATION DEBUG] User response: {result}")
            
            # Process result
            if result:
                # User confirmed - process attendance
                success, message = self.process_attendance_with_location_check(
                    face['nric'], "face_recognition"
                )
                
                if success:
                    print(f"[FACE DEBUG] Attendance success: {message}")
                    if message != "Location selection initiated":
                        self.show_success_message(f"✓ {employee['name']} - {message}")
                else:
                    print(f"[FACE DEBUG] Attendance failed: {message}")
                    
                    # Check if this is an early clock-out error
                    if self.is_early_clockout_error(message):
                        self.handle_early_clockout_error(employee['name'], message)
                    else:
                        self.show_error_message(f"✗ {message}")
                
                # Keep camera OFF after successful processing
                print(f"[CONFIRMATION DEBUG] Keeping camera OFF after successful face processing")
                
            else:
                # User rejected - keep camera OFF, let them manually try again
                print(f"[FACE DEBUG] Recognition rejected by user: {face['name']}")
                
                self.show_error_message("❌ Face recognition rejected\n\nPress + to try recognition again")
                
                # Keep camera OFF - employee must manually press + to try again
                print(f"[CONFIRMATION DEBUG] Camera remains OFF - manual activation required for retry")
                
        except Exception as e:
            print(f"Error in face recognition confirmation: {e}")
            print(f"[CONFIRMATION DEBUG] Exception traceback: {traceback.format_exc()}")
            # Keep camera OFF in case of error - manual activation required
            self.show_error_message("Error in face recognition confirmation\n\nPress + to try again")

    def show_success_message(self, message):
        """Show success message"""
        self.message_frame.pack(fill="x", padx=30, pady=10)
        self.message_label.configure(text=message, text_color="green")
        self.status_label.configure(text="● SUCCESS", text_color="green")
        
        # Update attendance history when someone scans
        self.update_attendance_history()
        
        # Auto-hide after timeout
        self.root.after(self.auto_timeout * 1000, self.clear_message)
    
    def show_error_message(self, message):
        """Show error message"""
        self.message_frame.pack(fill="x", padx=30, pady=10)
        self.message_label.configure(text=message, text_color="red")
        self.status_label.configure(text="● ERROR", text_color="red")
        
        # Auto-hide after timeout
        self.root.after(self.auto_timeout * 1000, self.clear_message)
    
    def show_auto_dismiss_error(self, message, dismiss_after=3):
        """Show auto-dismissing error popup window for face recognition errors"""
        # Pause camera when popup appears
        self.pause_camera_for_popup()
        
        error_popup = ctk.CTkToplevel(self.root)
        error_popup.title("Error")
        error_popup.geometry("400x200")
        error_popup.transient(self.root)
        error_popup.attributes('-topmost', True)
        
        error_popup.overrideredirect(True)  # This removes title bar completely
        
        popup_width = 400
        popup_height = 200
        x = self.root.winfo_rootx() + (self.root.winfo_width() - popup_width) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - popup_height) // 2
        error_popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        
        # Error content
        error_frame = ctk.CTkFrame(error_popup, fg_color="transparent")
        error_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Error icon
        icon_label = ctk.CTkLabel(
            error_frame,
            text="⚠️",
            font=ctk.CTkFont(size=48)
        )
        icon_label.pack(pady=(10, 10))
        
        # Error message
        message_label = ctk.CTkLabel(
            error_frame,
            text=message,
            font=ctk.CTkFont(size=16),
            text_color="red",
            wraplength=350
        )
        message_label.pack(pady=10)
        
        # Countdown label
        countdown_label = ctk.CTkLabel(
            error_frame,
            text=f"Closing in {dismiss_after} seconds...",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        countdown_label.pack(pady=(10, 0))
        
        # Auto-dismiss countdown
        def countdown(remaining):
            if remaining > 0:
                countdown_label.configure(text=f"Closing in {remaining} seconds...")
                error_popup.after(1000, lambda: countdown(remaining - 1))
            else:
                error_popup.destroy()
                # Resume camera after popup closes
                self.resume_camera_after_popup()
        
        countdown(dismiss_after)
    
    def play_scan_detected_beep(self):
        """Play quick beep when face or QR is detected (before processing)"""
        if not self.audio_enabled or not AUDIO_AVAILABLE:
            return
        
        def play_audio():
            try:
                if PYGAME_AVAILABLE:
                    # Try to play MP3 file using pygame
                    if os.path.exists("scan.mp3"):
                        sound = pygame.mixer.Sound("scan.mp3")
                        sound.play()
                        print("[AUDIO] Playing scan.mp3 via pygame (detection)")
                    else:
                        print("[AUDIO] scan.mp3 not found, falling back to beep")
                        # Fallback to system beep if MP3 not found
                        if WINSOUND_AVAILABLE:
                            winsound.Beep(600, 100)
                        else:
                            os.system('echo \a')
                elif WINSOUND_AVAILABLE:
                    # Fallback to winsound beep
                    winsound.Beep(600, 100)
                    print("[AUDIO] Playing detection beep via winsound")
                else:
                    # Final fallback to system beep
                    os.system('echo \a')
                    print("[AUDIO] Playing system detection beep")
            except Exception as e:
                print(f"[AUDIO] Error playing detection beep: {e}")
                # Emergency fallback
                try:
                    os.system('echo \a')
                except:
                    pass
        
        # Play audio in background thread to avoid blocking UI
        threading.Thread(target=play_audio, daemon=True).start()
    
    def show_early_clockout_error(self, employee_name, min_time, shift_name):
        """Show dedicated error dialog for early clock-out attempts"""
        # Create a modal dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Clock-Out Restricted")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"500x300+{x}+{y}")
        
        # Configure dialog
        dialog.configure(fg_color=("gray90", "gray10"))
        dialog.resizable(False, False)
        
        # Main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Error icon and title
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(10, 20))
        
        error_label = ctk.CTkLabel(
            title_frame,
            text="⚠️ CLOCK-OUT RESTRICTED",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="red"
        )
        error_label.pack()
        
        # Employee name
        name_label = ctk.CTkLabel(
            main_frame,
            text=f"Employee: {employee_name}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        name_label.pack(pady=(0, 15))
        
        # Main message
        message_label = ctk.CTkLabel(
            main_frame,
            text=f"You cannot clock out before {min_time}",
            font=ctk.CTkFont(size=14),
            text_color="red"
        )
        message_label.pack(pady=(0, 10))
        
        # Current time display
        current_time = datetime.now().strftime("%I:%M %p")
        time_label = ctk.CTkLabel(
            main_frame,
            text=f"Current Time: {current_time}",
            font=ctk.CTkFont(size=12)
        )
        time_label.pack(pady=(0, 20))
        
        # OK button
        ok_button = ctk.CTkButton(
            main_frame,
            text="OK",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=100,
            height=35,
            command=dialog.destroy
        )
        ok_button.pack(pady=(10, 10))
        
        # Auto-focus the OK button
        ok_button.focus_set()
        
        # Bind Enter key to close dialog
        dialog.bind('<Return>', lambda e: dialog.destroy())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def is_early_clockout_error(self, message):
        """Check if error message is about early clock-out"""
        return "Cannot clock out before" in message
    
    def handle_early_clockout_error(self, employee_name, message):
        """Handle early clock-out error with custom dialog"""
        # Parse the error message to extract time and shift info
        # Message format: "Cannot clock out before 5:00 PM (Early Shift)"
        import re
        match = re.search(r'Cannot clock out before (\d{1,2}:\d{2} [AP]M) \(([^)]+)\)', message)
        
        if match:
            min_time = match.group(1)
            shift_name = match.group(2)
        else:
            # Fallback if parsing fails
            min_time = "5:00 PM"
            shift_name = "Shift"
        
        # Show the custom dialog
        self.show_early_clockout_error(employee_name, min_time, shift_name)
    
    def clear_message(self):
        """Clear status message"""
        self.message_frame.pack_forget()
        self.status_label.configure(
            text="Please position yourself in front of the camera",
            text_color="green"
        )
    
    def load_known_faces(self):
        """Load known faces from database (now using face vectors)"""
        print("[FACE DEBUG] Loading known faces from database...")
        
        # Try to load face vectors first (new method)
        employees_with_vectors = self.db.get_all_face_vectors()
        
        if employees_with_vectors:
            print(f"[FACE DEBUG] Found {len(employees_with_vectors)} employees with face vectors")
            for emp in employees_with_vectors:
                print(f"[FACE DEBUG] - {emp['name']} ({emp['nric']}): Vector loaded")
            # Pass the database manager instead of the list
            self.face_recognition.load_known_faces(self.db)
        else:
            print("[FACE DEBUG] No face vectors found")
    
    def convert_and_load_legacy_faces(self, employees_with_faces):
        """Convert legacy face images to vectors on-the-fly (for backward compatibility)"""
        converted_employees = []
        
        for emp in employees_with_faces:
            try:
                # Load the image file and extract embedding
                import cv2
                img = cv2.imread(emp['face_image_path'])
                if img is not None:
                    face_vector, _ = self.face_recognition.extract_face_embedding_hybrid(img)
                    if face_vector is not None:
                        converted_employees.append({
                            'nric': emp['nric'],
                            'name': emp['name'],
                            'face_vector': face_vector
                        })
                        print(f"[FACE DEBUG] ✓ Converted {emp['name']} image to vector")
                    else:
                        print(f"[FACE DEBUG] ✗ Failed to extract face from {emp['name']} image")
                else:
                    print(f"[FACE DEBUG] ✗ Could not load image file for {emp['name']}")
            except Exception as e:
                print(f"[FACE DEBUG] ✗ Failed to convert {emp['name']} image: {e}")
        
        if converted_employees:
            # Store converted employees in database first, then load them properly
            for emp in converted_employees:
                # Convert and save each employee's face vector
                try:
                    success = self.db.add_employee_with_face_vector(
                        nric=emp['nric'],
                        name=emp['name'],
                        face_vector=emp['face_vector'],
                        department=emp.get('department', 'Unknown')
                    )
                    if success:
                        print(f"[FACE DEBUG] ✓ Migrated {emp['name']} to vector format")
                except Exception as e:
                    print(f"[FACE DEBUG] ✗ Failed to migrate {emp['name']}: {e}")
            
            # Now load from database properly
            self.face_recognition.load_known_faces(self.db)
    
    def update_attendance_history(self):
        """Update the unified attendance history display"""
        # Use the unified history frame
        history_frame = self.unified_history_frame
        
        # Clear existing history
        for widget in history_frame.winfo_children():
            widget.destroy()
        
        # Get today's attendance with explicit date check
        attendance_records = self.db.get_attendance_today()
        
        # Filter for today's records (all types - clock and check)
        current_date = datetime.now().strftime("%Y-%m-%d")
        unified_records = []
        for record in attendance_records:
            record_date = record['timestamp'][:10]  # Extract YYYY-MM-DD part
            if record_date == current_date:
                unified_records.append(record)
        
        if not unified_records:
            no_records_label = ctk.CTkLabel(
                history_frame,
                text=f"No attendance records for {current_date}",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            no_records_label.pack(pady=20)
            return
        
        # Group records by employee and keep all records (both clock and check)
        employee_records = {}
        for record in unified_records:  # Use all filtered records
            emp_id = record['nric']
            if emp_id not in employee_records:
                # Get employee info from database to include role
                employee_info = self.db.get_employee(emp_id)
                role = employee_info.get('role', 'Staff') if employee_info else 'Staff'
                
                employee_records[emp_id] = {
                    'name': record['name'],
                    'role': role,
                    'records': []
                }
            employee_records[emp_id]['records'].append(record)
        
        # Sort records by time for each employee (newest first)
        for emp_id in employee_records:
            employee_records[emp_id]['records'].sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Display all records for each employee
        for emp_id, data in employee_records.items():
            self.create_employee_history_section_unified(emp_id, data, history_frame)
    
    def create_employee_history_section_unified(self, nric, data, history_frame):
        """Create a section showing all attendance records for one employee in unified view"""
        # Main frame for this employee - enhanced styling with purple theme for unified view
        border_color = ("#8A2BE2", "#DDA0DD")  # BlueViolet and Plum colors
        main_frame = ctk.CTkFrame(
            history_frame, 
            border_width=2, 
            border_color=border_color,
            fg_color=("gray95", "gray15")
        )
        main_frame.pack(fill="x", padx=8, pady=12)
        
        # Employee header - larger and more prominent
        header_frame = ctk.CTkFrame(main_frame, fg_color=("#8A2BE2", "#663399"))  # BlueViolet and RebeccaPurple
        header_frame.pack(fill="x", padx=6, pady=6)
        
        # Employee info in horizontal layout
        info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=15)
        
        # Left side - name and ID
        left_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="x", expand=True)
        
        # Get role with appropriate icon
        role = data.get('role', 'Staff')
        
        name_label = ctk.CTkLabel(
            left_frame,
            text=f"👤 {data['name']} ({role})",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        name_label.pack(anchor="w")
        
        id_label = ctk.CTkLabel(
            left_frame,
            text=f"ID: {nric}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        id_label.pack(anchor="w")
        
        # Right side - current status info
        right_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        right_frame.pack(side="right")
        
        # Get the latest record to determine current status
        latest_record = data['records'][0] if data['records'] else None
        
        if latest_record:
            attendance_type = latest_record.get('attendance_type', 'check').lower()
            status = latest_record.get('status', 'unknown').lower()
            
            # Format the status text
            if attendance_type == 'clock':
                if status == 'in':
                    current_status = "Clock In"
                else:
                    current_status = "Clock Out"
            else:  # check
                if status == 'in':
                    current_status = "Check In"
                else:
                    current_status = "Check Out"
        else:
            current_status = "No Records"
        
        status_label = ctk.CTkLabel(
            right_frame,
            text=f"Current Status: {current_status}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        )
        status_label.pack()
        
        # Records container
        records_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        records_frame.pack(fill="x", padx=8, pady=4)
        
        # Display each record
        for i, record in enumerate(data['records']):
            self.create_record_entry_unified(record, records_frame, i)
    
    def create_record_entry_unified(self, record, records_frame, index):
        """Create a single attendance record entry for unified view - larger fonts and better spacing"""
        # Record frame with better styling - increased height for larger fonts
        bg_color = ("gray90", "gray20") if index % 2 == 0 else ("white", "gray25")
        record_frame = ctk.CTkFrame(records_frame, fg_color=bg_color, height=50)
        record_frame.pack(fill="x", pady=2, padx=5)
        record_frame.pack_propagate(False)
        
        # Parse timestamp
        record_time = datetime.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
        time_str = record_time.strftime("%H:%M:%S")
        
        # Status and type indicators
        status_text = "IN" if record['status'] == 'in' else "OUT"
        status_color = "lightgreen" if record['status'] == 'in' else "red"
        status_icon = "⚫"
        
        attendance_type = record.get('attendance_type', 'check').upper()
        type_color = "green" if attendance_type == 'CLOCK' else "blue"
        type_icon = "🕐" if attendance_type == 'CLOCK' else "✅"
        
        # Method indicator (shorter)
        method_text = {
            'face_recognition': '👤 Face',
            'qr_code': '🔍 QR', 
            'manual': '⌨️ Manual'
        }.get(record['method'], f"📋 {record['method']}")
        
        # Single line layout with better proportions to fill the width
        info_frame = ctk.CTkFrame(record_frame, fg_color="transparent")
        info_frame.pack(fill="both", expand=True, padx=12, pady=8)
        
        # Time (fixed width for alignment)
        time_label = ctk.CTkLabel(
            info_frame,
            text=time_str,
            font=ctk.CTkFont(size=18, weight="bold"),
            width=120,  # Fixed width for consistent alignment
            anchor="w"
        )
        time_label.pack(side="left", padx=(0, 10))
        
        # Create separate labels for better alignment
        # Type label (fixed width)
        type_label = ctk.CTkLabel(
            info_frame,
            text=f"{type_icon} {attendance_type}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=type_color,
            width=120,  # Fixed width for TYPE column
            anchor="w"
        )
        type_label.pack(side="left", padx=(0, 5))
        
        # Status label (fixed width)
        status_label = ctk.CTkLabel(
            info_frame,
            text=f"{status_icon} {status_text}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=type_color,
            width=80,  # Fixed width for STATUS column
            anchor="w"
        )
        status_label.pack(side="left", padx=(0, 5))
        
        # Special indicators (LATE/OT) with fixed width
        special_indicator_label = ctk.CTkLabel(
            info_frame,
            text="",  # Default empty
            font=ctk.CTkFont(size=16, weight="bold"),
            width=100,  # Fixed width for special indicators
            anchor="w"
        )
        
        # Add LATE indicator with orange color
        if record.get('late', False) and attendance_type == 'CLOCK':
            special_indicator_label.configure(
                text="⚠️ LATE",
                text_color="orange"
            )
        # Add OT indicator with purple color
        elif record.get('overtime_hours', 0) > 0 and attendance_type == 'CLOCK' and status_text == 'OUT':
            ot_hours = record.get('overtime_hours', 0)
            special_indicator_label.configure(
                text=f"🕐 OT {ot_hours}h",
                text_color="purple"
            )
        
        special_indicator_label.pack(side="left", padx=(0, 10))
        
        # Method (fixed width for alignment)
        method_label = ctk.CTkLabel(
            info_frame,
            text=method_text,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=130,  # Fixed width for consistent alignment
            anchor="w"
        )
        method_label.pack(side="left", padx=(0, 10))
        
        # Location (if applicable) - fill remaining space with larger font
        if attendance_type == 'CHECK' and status_text == 'OUT' and record.get('location_name'):
            location_label = ctk.CTkLabel(
                info_frame,
                text=f"📍 {record['location_name']}",
                font=ctk.CTkFont(size=20, weight="normal"),
                text_color="red",
                anchor="w"
            )
            location_label.pack(side="left", fill="x", expand=True)

    def create_single_record_entry(self, parent, record, index):
        """Create a single attendance record entry - enhanced for larger display"""
        # Record frame with better styling and more space
        bg_color = ("gray90", "gray20") if index % 2 == 0 else ("white", "gray25")
        record_frame = ctk.CTkFrame(parent, fg_color=bg_color, height=50)
        record_frame.pack(fill="x", pady=3, padx=5)
        record_frame.pack_propagate(False)
        
        # Parse timestamp
        record_time = datetime.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
        time_str = record_time.strftime("%H:%M:%S")
        date_str = record_time.strftime("%b %d")
        
        # Status indicator
        status_text = "IN" if record['status'] == 'in' else "OUT"
        status_color = "lightgreen" if record['status'] == 'in' else "red"
        status_icon = "🟢" if record['status'] == 'in' else "🔴"
        
        # Method indicator with icons
        method_icons = {
            'face_recognition': 'Face Recognition',
            'qr_code': 'QR/Barcode', 
            'manual': 'Manual Entry'
        }
        method_text = method_icons.get(record['method'], f"📋 {record['method']}")
        
        # Create main horizontal layout with better spacing
        info_frame = ctk.CTkFrame(record_frame, fg_color="transparent")
        info_frame.pack(fill="both", expand=True, padx=15, pady=8)
        
        # Time section (left) - larger and more prominent
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
        
        # Status section (center) - more prominent with attendance type
        status_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        status_frame.pack(side="left", fill="both", expand=True, padx=20)
        
        # Get attendance type (default to CLOCK for existing records)
        attendance_type = record.get('attendance_type', 'CLOCK')
        
        # Build status display with location for CHECK records and late indicator
        is_late_clock_in = record.get('late', False) and attendance_type.upper() == 'CLOCK' and record['status'] == 'in'
        
        # Check for location text (for CHECK OUT records)
        location_text = ""
        if attendance_type.upper() == 'CHECK' and record['status'] == 'out':
            location_name = record.get('location_name', '')
            if location_name:
                # Truncate location name if too long - set to 30 characters
                if len(location_name) > 25:
                    location_name = location_name[:22] + "..."
                location_text = f"\n📍 {location_name}"
        
        if is_late_clock_in:
            # Create mixed-color status display for late clock-in
            mixed_record_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
            mixed_record_frame.pack(expand=True)
            
            # Icon and LATE in red on first line
            first_line_frame = ctk.CTkFrame(mixed_record_frame, fg_color="transparent")
            first_line_frame.pack()
            
            icon_label = ctk.CTkLabel(
                first_line_frame,
                text=f"{status_icon} ",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=status_color
            )
            icon_label.pack(side="left")
            
            late_label = ctk.CTkLabel(
                first_line_frame,
                text="LATE ",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="red"
            )
            late_label.pack(side="left")
            
            rest_label = ctk.CTkLabel(
                first_line_frame,
                text=f"{attendance_type} {status_text}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=status_color
            )
            rest_label.pack(side="left")
            
            # Add location text if present
            if location_text:
                location_label = ctk.CTkLabel(
                    mixed_record_frame,
                    text=location_text,
                    font=ctk.CTkFont(size=14),
                    text_color=status_color
                )
                location_label.pack()
        else:
            # Normal single-color status display
            status_text_full = f"{status_icon} {attendance_type} {status_text}{location_text}"
            
            status_label = ctk.CTkLabel(
                status_frame,
                text=status_text_full,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=status_color,
                anchor="center",
                justify="center"
            )
            status_label.pack(expand=True)
        
        # Method section (right) - more descriptive
        method_frame = ctk.CTkFrame(info_frame, fg_color="transparent", width=150)
        method_frame.pack(side="right", fill="y")
        method_frame.pack_propagate(False)
        
        method_label = ctk.CTkLabel(
            method_frame,
            text=method_text,
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray"),
            anchor="e"
        )
        method_label.pack(expand=True)
    
    
    def start_camera(self):
        """Start camera"""
        print("[CAMERA DEBUG] Attempting to start camera...")
        
        # Clear any registration pause flags when user manually starts camera
        if hasattr(self, 'main_camera_paused'):
            self.main_camera_paused = False
            print("[CAMERA DEBUG] Cleared registration pause flag - user manually starting camera")
        
        if self.camera_manager.start_camera():
            self.camera_active = True
            
            # Clear any cached recognition results for a fresh start
            self.face_recognition.clear_latest_results()
            print("[CAMERA DEBUG] Cleared cached recognition results for fresh start")
            
            # Set camera start time to ignore immediate recognition results
            self.camera_start_time = time.time()
            
            print("[CAMERA DEBUG] Camera started successfully")
        else:
            print("[CAMERA DEBUG] Failed to start camera")
            self.show_error_message("Cannot start camera")
    
    def stop_camera(self):
        """Stop camera"""
        print("[CAMERA DEBUG] Stopping camera...")
        self.camera_manager.stop_camera()
        self.camera_active = False
        
        # Clear cached recognition results to prevent old results from triggering dialogs
        self.face_recognition.clear_latest_results()
        print("[CAMERA DEBUG] Cleared cached recognition results")
        
        # Clear the camera display and show manual activation instructions
        self.camera_label.configure(
            image="", 
            text="📷 Camera Off\n\nPress Numpad +\nto activate camera for recognition"
        )
        print("[CAMERA DEBUG] Camera stopped")
    
    def toggle_camera(self):
        """Manual camera activation for recognition"""
        if not self.camera_active:
            # Start camera for recognition
            self.start_camera()
            if self.camera_active:
                self.show_success_message("📷 Camera activated for recognition\n\nPosition your face in front of the camera")
                print("[CAMERA DEBUG] Camera manually activated for recognition")
        else:
            # Camera is already active - this shouldn't happen in new workflow
            print("[CAMERA DEBUG] Camera already active - this is unexpected in manual mode")
            self.show_success_message("📷 Camera is already active")
    
    def update_loop(self):
        """Main update loop with comprehensive error handling"""
        try:
            # Update time
            current_time = datetime.now().strftime("%A, %B %d, %Y - %H:%M:%S")
            self.time_label.configure(text=current_time)
            
            # Update attendance history every 30 seconds
            current_timestamp = time.time()
            if current_timestamp - self.last_history_update > 30:
                self.update_attendance_history()
                self.last_history_update = current_timestamp
            
            # Check focus every 10 seconds to maintain keyboard control
            if not hasattr(self, 'last_focus_check'):
                self.last_focus_check = 0
            if current_timestamp - self.last_focus_check > 10:
                self.maintain_focus()
                self.last_focus_check = current_timestamp
            
            # Process camera with error handling
            if self.camera_active:
                try:
                    self.process_camera()
                except Exception as cam_e:
                    print(f"[UPDATE ERROR] Camera processing failed: {cam_e}")
                    # Force garbage collection on camera errors
                    import gc
                    collected = gc.collect()
                    print(f"[GC ERROR] Collected {collected} objects after camera error")
            
        except Exception as e:
            print(f"[UPDATE ERROR] Exception in main update loop: {e}")
            import traceback
            traceback.print_exc()
            # Force garbage collection on any update error
            import gc
            collected = gc.collect()
            print(f"[GC ERROR] Collected {collected} objects after update error")
        
        finally:
            # Always schedule next update (16ms ≈ 60 FPS for smoother video)
            try:
                self.root.after(16, self.update_loop)
            except Exception as e:
                print(f"[SCHEDULE ERROR] Failed to schedule next update: {e}")
                # Try with longer delay as fallback
                try:
                    self.root.after(50, self.update_loop)
                except:
                    print("[CRITICAL ERROR] Cannot schedule updates - application may freeze")
    
    def update_loop(self):
        """Main update loop with comprehensive error handling"""
        try:
            # Update time
            current_time = datetime.now().strftime("%A, %B %d, %Y - %H:%M:%S")
            self.time_label.configure(text=current_time)
            
            # Update attendance history every 30 seconds
            current_timestamp = time.time()
            if current_timestamp - self.last_history_update > 30:
                self.update_attendance_history()
                self.last_history_update = current_timestamp
            
            # Check focus every 10 seconds to maintain keyboard control
            if not hasattr(self, 'last_focus_check'):
                self.last_focus_check = 0
            if current_timestamp - self.last_focus_check > 10:
                self.maintain_focus()
                self.last_focus_check = current_timestamp
            
            # Process camera with error handling
            if self.camera_active:
                try:
                    self.process_camera()
                except Exception as cam_e:
                    print(f"[UPDATE ERROR] Camera processing failed: {cam_e}")
                    # Force garbage collection on camera errors
                    import gc
                    collected = gc.collect()
                    print(f"[GC ERROR] Collected {collected} objects after camera error")
            
        except Exception as e:
            print(f"[UPDATE ERROR] Exception in main update loop: {e}")
            import traceback
            traceback.print_exc()
            # Force garbage collection on any update error
            import gc
            collected = gc.collect()
            print(f"[GC ERROR] Collected {collected} objects after update error")
        
        finally:
            # Always schedule next update (16ms ≈ 60 FPS for smoother video)
            try:
                self.root.after(16, self.update_loop)
            except Exception as e:
                print(f"[SCHEDULE ERROR] Failed to schedule next update: {e}")
                # Try with longer delay as fallback
                try:
                    self.root.after(50, self.update_loop)
                except:
                    print("[CRITICAL ERROR] Cannot schedule updates - application may freeze")
    
    def process_camera(self):
        """Process camera feed with error handling and restart capability"""
        try:
            # Skip camera processing if camera is not active (manual mode)
            if not self.camera_active:
                return  # Camera is OFF, no processing needed
                
            # Check if main camera is paused (e.g., during registration)
            if hasattr(self, 'main_camera_paused') and self.main_camera_paused:
                # Debug output only once per pause to avoid spam
                if not hasattr(self, '_pause_debug_shown') or not self._pause_debug_shown:
                    print("[CAMERA DEBUG] Main camera processing paused for registration")
                    # Show paused status on camera display
                    try:
                        self.camera_label.configure(image="", text="📷 Camera Paused\n(Registration Active)")
                    except:
                        pass
                    self._pause_debug_shown = True
                return  # Skip camera processing when paused
            
            # Reset debug flag when not paused
            if hasattr(self, '_pause_debug_shown'):
                if self._pause_debug_shown:
                    print("[CAMERA DEBUG] Main camera processing resumed")
                self._pause_debug_shown = False
            
            # Read frame with error checking
            frame = self.camera_manager.read_frame()
            if frame is None:
                # Try to restart camera if read fails multiple times
                if not hasattr(self, 'camera_fail_count'):
                    self.camera_fail_count = 0
                self.camera_fail_count += 1
                
                if self.camera_fail_count > 30:  # 30 failed reads in a row
                    print("[CAMERA ERROR] Multiple camera read failures, attempting restart...")
                    self.restart_camera()
                    self.camera_fail_count = 0
                return
            
            # Reset failure count on successful read
            if hasattr(self, 'camera_fail_count'):
                self.camera_fail_count = 0
            
            # Resize for display - smaller to fit in the compact camera frame
            height, width = frame.shape[:2]
            display_width = 450  # Reduced from 600 to fit better
            display_height = int(height * display_width / width)
            # Limit height to fit in camera frame
            max_height = 350
            if display_height > max_height:
                display_height = max_height
                display_width = int(width * display_height / height)
            display_frame = cv2.resize(frame, (display_width, display_height))
            
            # Choose face detection method based on configuration
            if self.use_ultra_light_detection:
                # Use Ultra Light Face Detection for maximum performance
                recognized_faces = self._process_ultra_light_detection(frame, display_frame, display_width, display_height, width, height)
            else:
                # Use traditional DeepFace processing
                recognized_faces = self._process_deepface_detection(frame, display_frame, display_width, display_height, width, height)
            
            if recognized_faces:
                print(f"[FACE DEBUG] Detected {len(recognized_faces)} face(s)")
        
        except Exception as e:
            print(f"[CAMERA ERROR] Exception in camera processing: {e}")
            # Force garbage collection on camera errors
            import gc
            collected = gc.collect()
            print(f"[GC ERROR] Collected {collected} objects after camera error")
            return
            
        # Process recognized faces for attendance
        current_time = time.time()  # Add timing for recognition logic
        
        # Ignore recognition results for first 2 seconds after camera start to prevent immediate dialog
        if hasattr(self, 'camera_start_time') and (current_time - self.camera_start_time) < 2.0:
            print(f"[CAMERA DEBUG] Ignoring recognition results for {2.0 - (current_time - self.camera_start_time):.1f}s after camera start")
            return
        
        for face in recognized_faces:
            if face['nric']:
                # Check if personal scanning is active
                if hasattr(self, 'personal_scanning_active') and self.personal_scanning_active:
                    # Auto-fill employee ID in personal dialog
                    if hasattr(self, 'personal_id_entry'):
                        try:
                            # Check if widget is still valid before using it
                            if self.personal_id_entry.winfo_exists():
                                self.personal_id_entry.delete(0, tk.END)
                                self.personal_id_entry.insert(0, face['nric'])
                                print(f"[PERSONAL DEBUG] Face recognition auto-filled: {face['nric']}")
                            else:
                                print("[PERSONAL DEBUG] Personal entry widget no longer exists")
                                self.personal_scanning_active = False  # Reset flag if widget is gone
                        except tk.TclError as e:
                            print(f"[PERSONAL DEBUG] Error accessing personal entry widget: {e}")
                            self.personal_scanning_active = False  # Reset flag on error
                    return
                
                # Check if group scanning is active
                if hasattr(self, 'group_scanning_active') and self.group_scanning_active:
                    # Auto-fill employee ID in group dialog
                    if hasattr(self, 'group_current_id'):
                        try:
                            # Check if widget is still valid before using it
                            if self.group_current_id.winfo_exists():
                                self.group_current_id.delete(0, tk.END)
                                self.group_current_id.insert(0, face['nric'])
                                print(f"[GROUP DEBUG] Face recognition auto-filled: {face['nric']}")
                            else:
                                print("[GROUP DEBUG] Group entry widget no longer exists")
                                self.group_scanning_active = False  # Reset flag if widget is gone
                        except tk.TclError as e:
                            print(f"[GROUP DEBUG] Error accessing group entry widget: {e}")
                            self.group_scanning_active = False  # Reset flag on error
                    return
                
                print(f"[FACE DEBUG] Recognized employee: {face['name']} ({face['nric']})")
                employee = self.db.get_employee(face['nric'])
                
                # Play detection beep when face is recognized
                self.play_scan_detected_beep()
                
                # Process attendance directly without confirmation
                print(f"[FACE DEBUG] Processing attendance directly for: {face['name']}")
                success, message = self.process_attendance_with_location_check(
                    face['nric'], "face_recognition"
                )
                
                if success:
                    print(f"[FACE DEBUG] Attendance success: {message}")
                    if message != "Location selection initiated":
                        self.show_success_message(f"✓ {employee['name']} - {message}")
                else:
                    print(f"[FACE DEBUG] Attendance failed: {message}")
                    
                    # Check if this is an early clock-out error
                    if self.is_early_clockout_error(message):
                        self.handle_early_clockout_error(employee['name'], message)
                    else:
                        self.show_error_message(f"✗ {message}")
                
                return
            else:
                print(f"[FACE DEBUG] Detected unknown face")
        
        # Try QR code scanning
        detected_codes = self.barcode_scanner.scan_frame(frame)
        if detected_codes and len(detected_codes) > 0:
            # Get the first detected code and extract the employee ID
            first_code = detected_codes[0]
            nric = first_code.get('data')
            
            if nric:  # Valid employee ID found
                print(f"[DEBUG] nric is truthy: '{nric}'")
                # Check if personal scanning is active
                if hasattr(self, 'personal_scanning_active') and self.personal_scanning_active:
                    if hasattr(self, 'personal_id_entry'):
                        self.personal_id_entry.delete(0, tk.END)
                        self.personal_id_entry.insert(0, nric)
                        print(f"[PERSONAL DEBUG] QR scan auto-filled: {nric}")
                    return
                
                # Check if group scanning is active
                if hasattr(self, 'group_scanning_active') and self.group_scanning_active:
                    if hasattr(self, 'group_current_id'):
                        self.group_current_id.delete(0, tk.END)
                        self.group_current_id.insert(0, nric)
                        print(f"[GROUP DEBUG] QR scan auto-filled: {nric}")
                    return
                
                print(f"[QR SCAN DEBUG] Detected QR/Barcode: '{nric}' from data: '{first_code.get('data')}'")
                employee = self.db.get_employee(nric)
                if employee:
                    print(f"[QR SCAN DEBUG] Found employee: {employee['name']} ({employee['nric']})")
                    
                    # Play detection beep when QR code is recognized
                    self.play_scan_detected_beep()
                    
                    # Process QR code directly without confirmation - QR codes are unique and reliable
                    print(f"[QR SCAN DEBUG] Processing QR code directly for {employee['name']}")
                    
                    # Turn OFF camera after QR recognition (manual mode)
                    self.stop_camera()
                    print(f"[QR SCAN DEBUG] Camera turned OFF after QR recognition")
                    
                    # Process attendance directly
                    success, message = self.process_attendance_with_location_check(
                        employee['nric'], "qr_code"
                    )
                    
                    if success:
                        print(f"[QR SCAN DEBUG] Attendance success: {message}")
                        if message != "Location selection initiated":
                            self.show_success_message(f"✓ {employee['name']} - {message}")
                            # Play success beep for successful attendance
                            # self.()
                    else:
                        print(f"[QR SCAN DEBUG] Attendance failed: {message}")
                        # Play error beep for failed attendance
                        
                        # Check if this is an early clock-out error
                        if self.is_early_clockout_error(message):
                            self.handle_early_clockout_error(employee['name'], message)
                        else:
                            self.show_error_message(f"✗ {message}")
                else:
                    print(f"[QR SCAN DEBUG] Employee not found in database")
                    # Play error beep for unknown employee
                    
                    self.show_error_message(f"✗ Employee {nric} not found")
            else:
                print(f"[QR SCAN DEBUG] Invalid QR code data: '{first_code.get('data')}'")
                print(f"[DEBUG] nric is falsy: {nric}")
                print(f"[DEBUG] First code data: '{first_code.get('data')}'")
                print(f"[DEBUG] First code type: '{first_code.get('type')}'")

                print(f"[DEBUG] After extract_employee_id: '{nric}'")
                
                self.show_error_message(f"✗ Invalid QR code format")
            return
        else:
            # Only print this occasionally to avoid spam
            if hasattr(self, 'debug_counter'):
                self.debug_counter += 1
            else:
                self.debug_counter = 0
            
            if self.debug_counter % 300 == 0:  # Print every 300 frames (about every 5 seconds at 60 FPS)
                print(f"[QR SCAN DEBUG] No QR/Barcode detected in frame {self.debug_counter}")
        
        # Draw face boxes if any detected
        if recognized_faces:
            display_frame = self.face_recognition.draw_face_boxes_from_results(display_frame, recognized_faces)
        else:
            # No faces detected - show positioning guidance
            self._display_distance_feedback(display_frame, "Please position your face in the camera view", False)
        
        # Ensure display_frame is valid before color conversion
        if display_frame is None:
            print("[CAMERA ERROR] Display frame is None")
            return
        
        # Convert and display frame with error handling
        try:
            frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            frame_pil = Image.fromarray(frame_rgb)
            frame_tk = ImageTk.PhotoImage(frame_pil)
            
            self.camera_label.configure(image=frame_tk, text="")
            self.camera_label.image = frame_tk
        except Exception as e:
            print(f"[CAMERA ERROR] Failed to display frame: {e}")
            # Show error text instead of crashing
            try:
                self.camera_label.configure(image="", text="📷 Camera Error\nRestarting...")
            except:
                pass  # Ignore secondary errors
    
    def quit_app(self):
        """Quit application with confirmation"""
        print("[QUIT DEBUG] Quit requested - showing confirmation")
        
        # Create a full-screen overlay for confirmation
        self.quit_overlay = ctk.CTkToplevel(self.root)
        self.quit_overlay.title("Confirm Exit")
        self.quit_overlay.attributes('-fullscreen', True)
        self.quit_overlay.attributes('-topmost', True)
        self.quit_overlay.configure(fg_color=("gray10", "gray10"))  # Semi-transparent dark
        self.quit_overlay.transient(self.root)
        self.quit_overlay.grab_set()
        
        # Center the confirmation message
        confirm_frame = ctk.CTkFrame(
            self.quit_overlay,
            width=800,
            height=300,
            corner_radius=20,
            fg_color=("red", "darkred"),
            border_width=5,
            border_color="white"
        )
        confirm_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Confirmation message
        warning_label = ctk.CTkLabel(
            confirm_frame,
            text="⚠️",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="white"
        )
        warning_label.pack(pady=40)
        
        instruction_label = ctk.CTkLabel(
            confirm_frame,
            text="Press - again to EXIT\nPress Enter to CANCEL",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        instruction_label.pack(pady=20)
        
        # Force UI update
        self.root.update()
        print("[QUIT DEBUG] Confirmation overlay displayed")
        
        # Temporarily change key bindings for confirmation
        self.root.unbind('<KP_Subtract>')
        self.root.unbind('<minus>')
        self.root.unbind('<Return>')
        self.root.unbind('<KP_Enter>')
        
        self.quit_overlay.bind('<KP_Subtract>', lambda e: self.confirm_quit())     # Numpad - to confirm
        self.quit_overlay.bind('<minus>', lambda e: self.confirm_quit())           # Regular - to confirm
        self.quit_overlay.bind('<Return>', lambda e: self.cancel_quit())          # Enter to cancel
        self.quit_overlay.bind('<KP_Enter>', lambda e: self.cancel_quit())        # Numpad Enter to cancel
        self.quit_overlay.bind('<Escape>', lambda e: self.cancel_quit())          # ESC to cancel
        
        # Focus on overlay to capture keys
        self.quit_overlay.focus_set()
        
        # Auto-cancel after 5 seconds
        self.root.after(5000, self.cancel_quit)
    
    def confirm_quit(self):
        """Actually quit the application"""
        print("[QUIT DEBUG] Quit confirmed - exiting application")
        # Close the confirmation overlay
        if hasattr(self, 'quit_overlay') and self.quit_overlay:
            self.quit_overlay.destroy()
        # Stop background face processing
        if hasattr(self, 'face_recognition') and self.face_recognition:
            self.face_recognition.stop_background_processing()
        # Close MongoDB connection
        if hasattr(self, 'db') and self.db:
            self.db.close_connection()
        if self.camera_active:
            self.camera_manager.stop_camera()
        self.root.quit()
        self.root.destroy()
    
    def cancel_quit(self):
        """Cancel the quit operation"""
        print("[QUIT DEBUG] Quit canceled - returning to normal operation")
        # Close the confirmation overlay
        if hasattr(self, 'quit_overlay') and self.quit_overlay:
            self.quit_overlay.destroy()
            self.quit_overlay = None
        # Restore original key bindings
        self.setup_keyboard_shortcuts()
    
    def restart_camera(self):
        """Restart camera on failure"""
        try:
            print("[CAMERA RESTART] Stopping camera...")
            self.camera_manager.stop_camera()
            time.sleep(1)  # Brief pause
            
            print("[CAMERA RESTART] Reinitializing camera...")
            self.camera_manager = CameraManager()
            
            if self.camera_active:
                print("[CAMERA RESTART] Starting camera...")
                self.camera_manager.start_camera()
                print("[CAMERA RESTART] Camera restarted successfully")
            
        except Exception as e:
            print(f"[CAMERA RESTART] Failed to restart camera: {e}")
    
    def _calculate_face_center(self, bbox):
        """Calculate center point of face bounding box"""
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        return center_x, center_y
    
    def _calculate_face_distance(self, center1, center2, face_size):
        """Calculate normalized distance between two face centers"""
        import math
        distance = math.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
        return distance / face_size  # Normalize by face size
    
    def _should_trigger_recognition(self, face_bbox, detection_confidence):
        """
        Determine if face recognition should be triggered based on detection stability
        
        Args:
            face_bbox: Face bounding box (x1, y1, x2, y2)
            detection_confidence: Face detection confidence
            
        Returns:
            bool: True if recognition should be triggered
        """
        if not self.face_warmup_enabled:
            return True  # Skip warm-up if disabled
        
        current_time = time.time()
        self.frame_counter += 1
        
        # Calculate face properties
        x1, y1, x2, y2 = face_bbox
        face_center = self._calculate_face_center(face_bbox)
        face_size = max(x2 - x1, y2 - y1)  # Use larger dimension as face size
        
        # Create face identifier based on position (for tracking across frames)
        face_id = f"face_{int(face_center[0]/50)}_{int(face_center[1]/50)}"  # Grid-based ID
        
        # Check recognition cooldown
        if current_time - self.last_recognition_time < self.recognition_cooldown:
            return False
        
        # Initialize or update face tracking
        if face_id not in self.face_detection_history:
            self.face_detection_history[face_id] = {
                'first_seen': self.frame_counter,
                'last_seen': self.frame_counter,
                'centers': [face_center],
                'confidences': [detection_confidence],
                'bbox_history': [face_bbox],
                'stable_frames': 1
            }
            print(f"[WARMUP] New face detected: {face_id} at frame {self.frame_counter}")
            return False
        
        face_data = self.face_detection_history[face_id]
        face_data['last_seen'] = self.frame_counter
        face_data['centers'].append(face_center)
        face_data['confidences'].append(detection_confidence)
        face_data['bbox_history'].append(face_bbox)
        
        # Keep only recent history (last N frames)
        max_history = self.face_warmup_frames * 2
        if len(face_data['centers']) > max_history:
            face_data['centers'] = face_data['centers'][-max_history:]
            face_data['confidences'] = face_data['confidences'][-max_history:]
            face_data['bbox_history'] = face_data['bbox_history'][-max_history:]
        
        # Check if face has been stable for enough frames
        consecutive_frames = self.frame_counter - face_data['first_seen'] + 1
        
        if consecutive_frames >= self.face_warmup_frames:
            # Check face stability (movement should be minimal)
            recent_centers = face_data['centers'][-self.face_warmup_frames:]
            is_stable = True
            
            for i in range(1, len(recent_centers)):
                distance = self._calculate_face_distance(recent_centers[0], recent_centers[i], face_size)
                if distance > self.face_warmup_stability_threshold:
                    is_stable = False
                    break
            
            # Check confidence stability
            recent_confidences = face_data['confidences'][-self.face_warmup_frames:]
            avg_confidence = sum(recent_confidences) / len(recent_confidences)
            min_confidence = min(recent_confidences)
            
            confidence_stable = min_confidence > 0.5 and avg_confidence > 0.7
            
            if is_stable and confidence_stable:
                print(f"[WARMUP] Face {face_id} is stable for {consecutive_frames} frames - triggering recognition")
                print(f"[WARMUP] Average confidence: {avg_confidence:.3f}, Min confidence: {min_confidence:.3f}")
                self.last_recognition_time = current_time
                
                # Clean up old detections to prevent memory buildup
                self._cleanup_old_face_detections()
                return True
            else:
                stability_reason = "movement" if not is_stable else "confidence"
                print(f"[WARMUP] Face {face_id} not stable ({stability_reason}) - frames: {consecutive_frames}")
                return False
        
        print(f"[WARMUP] Face {face_id} warming up - frames: {consecutive_frames}/{self.face_warmup_frames}")
        return False
    
    def _cleanup_old_face_detections(self):
        """Clean up old face detection history to prevent memory buildup"""
        current_frame = self.frame_counter
        cleanup_threshold = self.face_warmup_frames * 5  # Keep history for 5x warmup period
        
        faces_to_remove = []
        for face_id, face_data in self.face_detection_history.items():
            if current_frame - face_data['last_seen'] > cleanup_threshold:
                faces_to_remove.append(face_id)
        
        for face_id in faces_to_remove:
            del self.face_detection_history[face_id]
            print(f"[WARMUP] Cleaned up old face detection: {face_id}")
    
    def _draw_warmup_status(self, display_frame, face_bbox, face_id, frames_remaining):
        """Draw warm-up status on the display frame"""
        x1, y1, x2, y2 = face_bbox
        
        # Draw progress bar above the face
        bar_width = x2 - x1
        bar_height = 8
        bar_x = x1
        bar_y = y1 - 20
        
        # Background bar
        cv2.rectangle(display_frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
        
        # Progress bar
        progress = max(0, (self.face_warmup_frames - frames_remaining) / self.face_warmup_frames)
        progress_width = int(bar_width * progress)
        
        if progress_width > 0:
            color = (0, 255, 255) if frames_remaining > 0 else (0, 255, 0)  # Yellow warming up, green ready
            cv2.rectangle(display_frame, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), color, -1)
        
        # Text
        warmup_text = f"Warming up... {self.face_warmup_frames - frames_remaining}/{self.face_warmup_frames}"
        if frames_remaining <= 0:
            warmup_text = "Ready for recognition!"
        
        cv2.putText(display_frame, warmup_text, (bar_x, bar_y - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    def _process_ultra_light_detection(self, frame, display_frame, display_width, display_height, width, height):
        """Process frame using Ultra Light Face Detection for maximum performance"""
        recognized_faces = []
        
        try:
            # Detect faces using ultra light detector
            detected_faces = self.ultra_light_detector.detect_faces_for_attendance(frame)
            
            if detected_faces:
                # Get the best face for attendance
                best_face = self.ultra_light_detector.get_best_face(detected_faces)
                
                # Check distance for the best face and provide feedback
                if best_face:
                    x1, y1, x2, y2 = best_face['bbox']
                    face_coords = (x1, y1, x2 - x1, y2 - y1)  # Convert to (x, y, w, h) format
                    is_good_distance, feedback_message = self._check_face_distance_and_provide_feedback(frame, face_coords)
                    
                    # Display distance feedback on the frame
                    self._display_distance_feedback(display_frame, feedback_message, is_good_distance)
                
                # Draw all detected faces on display frame
                display_faces_with_labels = []
                
                for face_data in detected_faces:
                    x1, y1, x2, y2 = face_data['bbox']
                    confidence = face_data['confidence']
                    
                    # Scale coordinates to display frame
                    display_x1 = int(x1 * display_width / width)
                    display_y1 = int(y1 * display_height / height)
                    display_x2 = int(x2 * display_width / width)
                    display_y2 = int(y2 * display_height / height)
                    
                    # Extract face region for recognition
                    face_region = frame[y1:y2, x1:x2]
                    
                    # Perform face recognition on the detected face
                    nric = None
                    employee_name = "Unknown"
                    recognition_confidence = 0.0
                    
                    print(f"[ULTRA DEBUG] Face region size: {face_region.shape if face_region.size > 0 else 'empty'}")
                    print(f"[ULTRA DEBUG] Bbox coordinates: ({x1}, {y1}, {x2}, {y2})")
                    
                    # Check if face recognition should be triggered (warm-up system)
                    should_recognize = self._should_trigger_recognition(face_data['bbox'], confidence)
                    
                    if face_region.size > 0 and face_region.shape[0] > 20 and face_region.shape[1] > 20 and should_recognize:  # Valid face region and passed warm-up
                        try:
                            print(f"[ULTRA DEBUG] Calling DeepFace recognition on face region...")
                            print(f"[ULTRA DEBUG] Face region shape: {face_region.shape}")
                            
                            # Use DeepFace recognition on the detected face region
                            recognized_id, rec_conf = self.face_recognition.recognize_face(face_region)
                            print(f"[ULTRA DEBUG] DeepFace returned: ID={recognized_id}, confidence={rec_conf}")
                            
                            # If direct recognition fails, try with some padding around the face
                            if not recognized_id:
                                print(f"[ULTRA DEBUG] , trying with padded region...")
                                
                                # Add padding around the detected face
                                padding = 30
                                padded_x1 = max(0, x1 - padding)
                                padded_y1 = max(0, y1 - padding) 
                                padded_x2 = min(frame.shape[1], x2 + padding)
                                padded_y2 = min(frame.shape[0], y2 + padding)
                                
                                padded_face_region = frame[padded_y1:padded_y2, padded_x1:padded_x2]
                                print(f"[ULTRA DEBUG] Padded region shape: {padded_face_region.shape}")
                                
                                if padded_face_region.size > 0:
                                    recognized_id, rec_conf = self.face_recognition.recognize_face(padded_face_region)
                                    print(f"[ULTRA DEBUG] Padded recognition returned: ID={recognized_id}, confidence={rec_conf}")
                            
                            if recognized_id:
                                nric = recognized_id
                                recognition_confidence = rec_conf
                                # Get employee name from database instead of known_faces
                                # This is more reliable as the recognition now returns NRIC not username
                                db_employee = self.db.get_employee(nric)
                                if db_employee:
                                    employee_name = db_employee.get('name', nric)
                                else:
                                    # Employee not found in database
                                    employee_name = nric
                                    print(f"[ULTRA RECOGNITION] NRIC {nric} not found in database")
                                    # Show auto-dismiss error message
                                    self.show_auto_dismiss_error(f"❌ Employee {nric} not found in database")
                                print(f"[ULTRA RECOGNITION] Face recognized: {employee_name} ({nric}) confidence: {rec_conf:.2f}")
                            else:
                                print(f"[ULTRA RECOGNITION] Face detected but not recognized (detection conf: {confidence:.2f})")
                                # Show auto-dismiss error for unrecognized face
                                self.show_auto_dismiss_error("❌ Face not recognized\nPlease register or try again")
                        except Exception as rec_error:
                            print(f"[ULTRA RECOGNITION] Recognition error: {rec_error}")
                    elif face_region.size > 0 and face_region.shape[0] > 20 and face_region.shape[1] > 20:
                        print(f"[ULTRA DEBUG] Face region valid but warm-up not complete - skipping recognition")
                    else:
                        print(f"[ULTRA DEBUG] Face region too small or invalid for recognition")
                    
                    # Create face data in format expected by main drawing system
                    is_best = best_face and face_data['id'] == best_face['id']
                    
                    # Get warm-up status for display
                    face_center = self._calculate_face_center(face_data['bbox'])
                    face_id = f"face_{int(face_center[0]/50)}_{int(face_center[1]/50)}"
                    
                    warmup_status = ""
                    frames_remaining = self.face_warmup_frames  # Default for new faces
                    
                    if self.face_warmup_enabled and face_id in self.face_detection_history:
                        face_data_history = self.face_detection_history[face_id]
                        frames_seen = self.frame_counter - face_data_history['first_seen'] + 1
                        frames_remaining = max(0, self.face_warmup_frames - frames_seen)
                        
                        if frames_remaining > 0:
                            warmup_status = f" [WARMUP {frames_seen}/{self.face_warmup_frames}]"
                        else:
                            warmup_status = " [READY]"
                    elif self.face_warmup_enabled:
                        warmup_status = f" [WARMUP 1/{self.face_warmup_frames}]"
                    
                    if nric:
                        # Recognized face
                        label = f"{employee_name} ({recognition_confidence:.2f}){warmup_status}"
                    else:
                        # Detected but unrecognized face
                        if should_recognize:
                            label = f"Face Detected {warmup_status}"
                        else:
                            label = f"Face Detected {warmup_status}"
                    
                    if is_best:
                        label += " [BEST]"
                    
                    face_result = {
                        'name': employee_name if nric else label,
                        'nric': nric,  # Now includes actual recognition results
                        'confidence': recognition_confidence if nric else confidence,
                        'position': (display_x1, display_y1, display_x2 - display_x1, display_y2 - display_y1),
                        'is_best': is_best,
                        'warmup_status': warmup_status.strip(),
                        'warmup_frames_remaining': frames_remaining
                    }
                    display_faces_with_labels.append(face_result)
                    
                    # Add to recognized_faces so main system can draw them
                    recognized_faces.append(face_result)
                
                # Don't draw faces here - let the main system handle it
                # display_frame = self._draw_ultra_light_faces(display_frame, display_faces_with_labels)
                
                # For attendance processing, we could integrate with recognition here
                # For now, ultra light detection is mainly for showing real-time face detection
                # You could add face recognition integration here if needed
            else:
                # No faces detected by Ultra Light detector - show positioning guidance
                self._display_distance_feedback(display_frame, "Please position your face in the camera view", False)
                
        except Exception as e:
            print(f"[ULTRA LIGHT ERROR] Detection processing failed: {e}")
        
        return recognized_faces
    
    def _process_deepface_detection(self, frame, display_frame, display_width, display_height, width, height):
        """Process frame using traditional DeepFace detection"""
        recognized_faces = []
        
        try:
            # Submit frame for background DeepFace processing (non-blocking)
            self.face_recognition.submit_frame_for_processing(frame)
            
            # Get latest recognition results from background thread
            face_results = self.face_recognition.get_latest_results()
            
            if face_results:
                # Check distance for the first detected face and provide feedback
                best_face = None
                best_confidence = 0.0
                
                # Find the face with highest confidence for distance checking
                for face in face_results:
                    if 'position' in face and face.get('confidence', 0.0) > best_confidence:
                        best_face = face
                        best_confidence = face.get('confidence', 0.0)
                
                if best_face:
                    x, y, w, h = best_face['position']
                    face_coords = (x, y, w, h)
                    is_good_distance, feedback_message = self._check_face_distance_and_provide_feedback(frame, face_coords)
                    
                    # Display distance feedback on the frame
                    self._display_distance_feedback(display_frame, feedback_message, is_good_distance)
                
                # Convert coordinates to display frame and draw faces
                display_faces_with_labels = []
                
                for face in face_results:
                    if 'position' in face:
                        face_confidence = face.get('confidence', 0.0)
                        x, y, w, h = face['position']
                        # Scale coordinates to display frame
                        display_x = int(x * display_width / width)
                        display_y = int(y * display_height / height)
                        display_w = int(w * display_width / width)
                        display_h = int(h * display_height / height)
                        
                        # Check confidence and handle accordingly
                        CONFIDENCE_THRESHOLD = 0.6  # Define threshold
                        if face_confidence < CONFIDENCE_THRESHOLD:
                            # Show low confidence faces with special label
                            print(f"[CONFIDENCE NOTICE] Low confidence detection: {face_confidence:.2f} < {CONFIDENCE_THRESHOLD}")
                            display_result = {
                                'name': 'Low Confidence',
                                'nric': None,
                                'confidence': face_confidence,
                                'position': (display_x, display_y, display_w, display_h)
                            }
                            display_faces_with_labels.append(display_result)
                            # Don't add to recognized_faces (no attendance processing)
                        else:
                            # High confidence face - process normally
                            display_result = {
                                'name': face.get('name'),
                                'nric': face.get('nric'),
                                'confidence': face.get('confidence', 0.0),
                                'position': (display_x, display_y, display_w, display_h)
                            }
                            display_faces_with_labels.append(display_result)
                            
                            # Store recognized faces for attendance processing
                            if face['nric']:
                                recognized_faces.append(face)
                                print(f"[FACE DEBUG] Recognized: {face['name']} (ID: {face['nric']}, confidence: {face['confidence']:.2f})")
                
                # Draw faces with proper labels using pure DeepFace results
                display_frame = self.face_recognition.draw_face_boxes_from_results(display_frame, display_faces_with_labels)
            else:
                # No faces detected by DeepFace - show positioning guidance
                self._display_distance_feedback(display_frame, "Please position your face in the camera view", False)
        
        except Exception as e:
            print(f"[DEEPFACE ERROR] Detection processing failed: {e}")
        
        return recognized_faces
    
    def _draw_ultra_light_faces(self, frame, faces_with_labels):
        """Draw face detection boxes for ultra light detector"""
        result_frame = frame.copy()
        
        for face in faces_with_labels:
            x, y, w, h = face['position']
            x2, y2 = x + w, y + h
            confidence = face['confidence']
            name = face['name']
            is_best = face.get('is_best', False)
            
            # Color coding
            color = (0, 255, 0) if is_best else (0, 255, 255)  # Green for best, yellow for others
            thickness = 3 if is_best else 2
            
            # Draw bounding box
            cv2.rectangle(result_frame, (x, y), (x2, y2), color, thickness)
            
            # Draw label with background
            label = name
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
            
            # Background for text
            cv2.rectangle(result_frame, 
                         (x, y - label_size[1] - 10), 
                         (x + label_size[0], y), 
                         color, -1)
            
            # Text
            cv2.putText(result_frame, label, (x, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Add performance overlay
        if hasattr(self, 'ultra_light_detector') and self.ultra_light_detector:
            fps = self.ultra_light_detector.get_performance_stats()['fps']
            cv2.putText(result_frame, f"Ultra Light FPS: {fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return result_frame
    
    def toggle_group_mode(self):
        """Toggle group check mode on/off"""
        is_group_mode = self.group_check_var.get()
        
        if is_group_mode:
            # Enable group mode
            self.group_list_frame.pack(fill="x", padx=15, pady=(0, 10))
            # Adjust camera label size to make room
            self.camera_label.configure(height=250)  # Reduce height when group mode is on
            print("[GROUP MODE] Group check mode enabled")
        else:
            # Disable group mode
            self.group_list_frame.pack_forget()
            # Restore camera label size
            self.camera_label.configure(height=400)  # Restore full height
            # Clear group list when disabling
            self.clear_group_list()
            print("[GROUP MODE] Group check mode disabled")
    
    def add_employee_to_group(self, nric, employee_name):
        """Add an employee to the group check list"""
        # Check if already in list
        for emp in self.group_employees:
            if emp['nric'] == nric:
                # Don't show notification here - it will be shown by the calling method
                # to maintain consistency with other group error notifications
                return False
        
        # Add to group
        self.group_employees.append({
            'nric': nric,
            'name': employee_name
        })
        
        # Update display
        self.update_group_display()
        print(f"[GROUP MODE] Added {employee_name} ({nric}) to group list")
        return True
    
    def update_group_display(self):
        """Update the visual display of the group list"""
        # Clear existing widgets in scroll frame
        for widget in self.group_scroll_frame.winfo_children():
            widget.destroy()
        
        # Add each employee to the display
        for i, emp in enumerate(self.group_employees):
            emp_frame = ctk.CTkFrame(self.group_scroll_frame)
            emp_frame.pack(fill="x", padx=5, pady=2)
            
            # Employee info
            emp_label = ctk.CTkLabel(
                emp_frame,
                text=f"{i+1}. {emp['name']} (ID: {emp['nric']})",
                font=ctk.CTkFont(size=12),
                anchor="w"
            )
            emp_label.pack(side="left", fill="x", expand=True, padx=10, pady=5)
            
            # Remove button
            remove_btn = ctk.CTkButton(
                emp_frame,
                text="✕",
                font=ctk.CTkFont(size=12),
                width=30,
                height=25,
                fg_color="red",
                hover_color="darkred",
                command=lambda idx=i: self.remove_from_group(idx)
            )
            remove_btn.pack(side="right", padx=5, pady=2)
        
        # Update button states
        has_employees = len(self.group_employees) > 0
        self.process_group_btn.configure(state="normal" if has_employees else "disabled")
    
    def remove_from_group(self, index):
        """Remove an employee from the group list"""
        if 0 <= index < len(self.group_employees):
            removed_emp = self.group_employees.pop(index)
            self.update_group_display()
            print(f"[GROUP MODE] Removed {removed_emp['name']} from group list")
    
    def clear_group_list(self):
        """Clear the entire group list"""
        self.group_employees.clear()
        self.update_group_display()
        print("[GROUP MODE] Group list cleared")
    
    def process_group_checkout(self):
        """Process checkout for all employees in the group"""
        if not self.group_employees:
            self.show_temp_message("No employees in group list!", "orange")
            return
        
        # Pause camera to prevent continuous face recognition during location selection
        self.pause_camera_for_popup()
        
        # Show location selector for the group
        def on_location_selected(location):
            # Resume camera after location selection (always, whether location selected or cancelled)
            self.resume_camera_after_popup()
            
            if location:
                successful_checkouts = []
                failed_checkouts = []
                
                current_time = self.attendance_manager.get_current_time()
                
                for emp in self.group_employees:
                    nric = emp['nric']
                    employee_name = emp['name']
                    
                    # Record attendance
                    record_id = self.db.record_attendance(nric, "manual", "out", "check", current_time)
                    
                    if record_id:
                        # Prepare location data for attendance record
                        location_data = {
                            "location_name": location.get('name', ''),
                            "address": location.get('address', '')
                        }
                        
                        # Update location for this record
                        success = self.db.update_attendance_location(record_id, location_data)
                        
                        if success:
                            successful_checkouts.append(employee_name)
                            print(f"[GROUP CHECKOUT] Successfully checked out {employee_name} with location")
                        else:
                            failed_checkouts.append(employee_name)
                            print(f"[GROUP CHECKOUT] Failed to save location for {employee_name}")
                    else:
                        failed_checkouts.append(employee_name)
                        print(f"[GROUP CHECKOUT] Failed to record attendance for {employee_name}")
                
                # Show results
                location_name = location.get('name', 'Selected location')
                if successful_checkouts:
                    if len(successful_checkouts) == 1:
                        success_msg = f"✅ Group checkout successful!\n\n{successful_checkouts[0]} checked out at {location_name}"
                    else:
                        success_msg = f"✅ Group checkout successful!\n\n{len(successful_checkouts)} employees checked out at {location_name}"
                    
                    if failed_checkouts:
                        success_msg += f"\n\n⚠️ Failed: {', '.join(failed_checkouts)}"
                    
                    self.show_success_message(success_msg)
                else:
                    self.show_error_message("✗ Group checkout failed for all employees")
                
                # Clear group list and update history
                self.clear_group_list()
                self.update_attendance_history()
                
                print(f"[GROUP CHECKOUT] Completed - Success: {len(successful_checkouts)}, Failed: {len(failed_checkouts)}")
            else:
                print("[GROUP CHECKOUT] Location selection cancelled")
        
        # Open location selector dialog
        from core.location_selector import LocationSelector
        LocationSelector(
            parent=self.root,
            nric=f"GROUP_{len(self.group_employees)}",  # Group identifier
            callback=on_location_selected
        )

def main():
    """Run the simple kiosk application"""
    app = SimpleKioskApp()
    try:
        app.root.mainloop()
    except KeyboardInterrupt:
        app.quit_app()

if __name__ == "__main__":
    main()
