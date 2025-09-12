#!/usr/bin/env python3
"""
Scanner-Only Kiosk Attendance System
Optimized for barcode/QR code scanners without camera
Keyboard and numpad operation only
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
import re
from datetime import datetime

# Import core modules
from core.database import DatabaseManager
from core.attendance import AttendanceManager

class ScannerKioskApp:
    def __init__(self):
        # Make application DPI-aware (must be done before creating tkinter window)
        try:
            import ctypes
            # Tell Windows this app is DPI-aware
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            print("[INIT DEBUG] Successfully set DPI awareness")
        except:
            print("[INIT DEBUG] Could not set DPI awareness (not critical)")
        
        # Initialize GUI
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Scanner Kiosk - Attendance System")
        
        # Initialize core components
        print("[INIT DEBUG] Initializing core components...")
        self.db = DatabaseManager()
        print("[INIT DEBUG] Database manager initialized")
        self.attendance_manager = AttendanceManager(self.db)
        print("[INIT DEBUG] Attendance manager initialized")
        
        # GUI state variables
        self.current_mode = "scanner"  # Always scanner mode
        self.auto_timeout = 3  # seconds to show result
        self.last_history_update = 0  # for periodic updates
        
        # Scanning cooldown to prevent rapid-fire scanning
        self.last_scan_time = 0  # timestamp of last successful scan
        self.scan_cooldown = 2.0  # seconds between scans
        
        # Scanner statistics
        self.scan_stats = {
            'total_scans': 0,
            'successful_scans': 0,
            'failed_scans': 0,
            'invalid_scans': 0,
            'session_start': time.time()
        }
        
        # Scanner input buffer
        self.scanner_buffer = ""
        self.last_input_time = 0
        self.scanner_timeout = 0.1  # seconds between characters from scanner
        self.min_scan_length = 3  # minimum valid scan length
        self.max_scan_length = 50  # maximum valid scan length
        self.scan_patterns = [r'^\d+$', r'^[A-Z0-9]+$']  # valid patterns
        
        # Audio feedback (Windows only)
        self.audio_enabled = True
        
        # Create GUI
        self.setup_kiosk_mode()
        self.create_interface()
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Start update loop
        self.update_loop()
    
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
            text="● SCANNER READY - Scan QR/Barcode or press Enter for manual entry",
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
                        text="● SCANNER READY - Scan QR/Barcode or press Enter for manual entry",
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
        
        # Content area - Full width for attendance history with minimal padding
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Single column layout - Attendance history takes full space
        self.create_attendance_display()
        
        # Bottom - Status and messages
        self.create_status_area()
    
    def create_header(self):
        """Create header with title and time"""
        header_frame = ctk.CTkFrame(self.main_frame, height=70)
        header_frame.pack(fill="x", padx=30, pady=10)
        header_frame.pack_propagate(False)
        
        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="ATTENDANCE SYSTEM",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=20)
        
        # Current time
        self.time_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=16)
        )
        self.time_label.pack(side="right", padx=20, pady=20)
    
    def create_attendance_display(self):
        """Create full-page attendance display"""
        # Title - more compact
        title_frame = ctk.CTkFrame(self.content_frame)
        title_frame.pack(fill="x", pady=(0, 10))
        
        # Main title - smaller font
        main_title = ctk.CTkLabel(
            title_frame,
            text="📊 TODAY'S ATTENDANCE",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="cyan"
        )
        main_title.pack(side="left", padx=15, pady=10)
        
        # Attendance list frame - Maximized space
        self.history_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            corner_radius=10
        )
        self.history_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Load initial attendance history
        self.update_attendance_history()
        
        # Control buttons at bottom - more compact
        button_frame = ctk.CTkFrame(self.content_frame)
        button_frame.pack(fill="x", pady=(5, 0))
        
        # Manual entry button
        self.manual_btn = ctk.CTkButton(
            button_frame,
            text="MANUAL ENTRY (Press Enter)",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=280,
            height=40,
            command=self.show_manual_entry
        )
        self.manual_btn.pack(side="left", padx=15, pady=8)
        
        # Mode indicator
        self.mode_label = ctk.CTkLabel(
            button_frame,
            text="SCANNER READY",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="green"
        )
        self.mode_label.pack(side="right", padx=15, pady=8)
        
        # Scanner statistics display
        self.stats_label = ctk.CTkLabel(
            button_frame,
            text="Scans: 0/0 (100%)",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.stats_label.pack(side="right", padx=(0, 15), pady=8)
        
        # Last scan display
        self.last_scan_display = ctk.CTkLabel(
            button_frame,
            text="Ready for scan",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.last_scan_display.pack(padx=15, pady=3)
    
    def create_status_area(self):
        """Create status and message area"""
        self.status_frame = ctk.CTkFrame(self.main_frame, height=60)
        self.status_frame.pack(fill="x", padx=30, pady=10)
        self.status_frame.pack_propagate(False)
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="● READY - Please scan your employee barcode/QR code",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="green"
        )
        self.status_label.pack(pady=20)
        
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
        # Help and navigation
        self.root.bind('<F1>', lambda e: self.show_help())
        self.root.bind('<F2>', lambda e: self.show_scanner_stats())
        self.root.bind('<F3>', lambda e: self.show_employee_lookup())
        self.root.bind('<F4>', lambda e: self.toggle_kiosk_mode())  # Add toggle for debugging
        self.root.bind('<Escape>', lambda e: self.clear_message())
        self.root.bind('<Alt-F4>', lambda e: self.quit_app())
        
        # Manual entry shortcuts
        self.root.bind('<Return>', lambda e: self.show_manual_entry())
        self.root.bind('<KP_Enter>', lambda e: self.show_manual_entry())
        
        # Exit shortcut
        self.root.bind('<KP_Subtract>', lambda e: self.quit_app())
        self.root.bind('<minus>', lambda e: self.quit_app())
        
        # Scanner input capture (capture all key presses)
        self.root.bind('<KeyPress>', self.handle_key_input)
        
        # Focus on root to capture keys - use multiple methods for reliability
        self.root.focus_set()
        self.root.focus_force()
        
        # Make the window always stay on top and grab focus
        self.root.attributes('-topmost', True)
        self.root.lift()
        
        print("[KEYBOARD DEBUG] Keyboard shortcuts configured and focus set")
    
    def handle_key_input(self, event):
        """Handle keyboard input for scanner data"""
        current_time = time.time()
        
        # Filter out control keys and function keys
        if event.keysym in ['F1', 'Return', 'KP_Enter', 'Escape', 'Alt_L', 'Alt_R', 
                           'Control_L', 'Control_R', 'Shift_L', 'Shift_R', 'Tab',
                           'KP_Subtract', 'minus']:
            return
        
        # Check if this might be scanner input (rapid character sequence)
        if current_time - self.last_input_time > self.scanner_timeout:
            # New scan sequence - clear buffer
            self.scanner_buffer = ""
        
        # Add character to buffer
        if event.char and event.char.isprintable():
            self.scanner_buffer += event.char
            self.last_input_time = current_time
            
            # Update display
            self.last_scan_display.configure(
                text=f"Scanning: {self.scanner_buffer}",
                text_color="yellow"
            )
            
            # Check if scan is complete (usually ends with Enter or after timeout)
            self.root.after(100, self.check_scan_complete)
    
    def play_beep(self, success=True):
        """Play audio feedback for scan results"""
        if not self.audio_enabled:
            return
        
        try:
            import winsound
            if success:
                # High beep for success
                winsound.Beep(1000, 200)
            else:
                # Lower beep for failure
                winsound.Beep(500, 300)
        except ImportError:
            # Fallback for non-Windows or missing winsound
            print('\a')  # System bell
    
    def validate_scan_data(self, scan_data):
        """Validate scanned data format"""
        import re
        
        # Check length
        if len(scan_data) < self.min_scan_length:
            return False, "Scan too short"
        if len(scan_data) > self.max_scan_length:
            return False, "Scan too long"
        
        # Check for valid patterns (numbers or alphanumeric)
        for pattern in self.scan_patterns:
            if re.match(pattern, scan_data):
                return True, "Valid scan"
        
        return False, "Invalid format"
    
    def check_scan_complete(self):
        """Check if scanner input is complete"""
        current_time = time.time()
        
        # If enough time has passed since last character, consider scan complete
        if (current_time - self.last_input_time > self.scanner_timeout and 
            len(self.scanner_buffer) > 0):
            
            scan_data = self.scanner_buffer.strip()
            self.scanner_buffer = ""
            
            # Update scan statistics
            self.scan_stats['total_scans'] += 1
            
            # Validate scan data
            is_valid, message = self.validate_scan_data(scan_data)
            
            if is_valid:
                self.process_scanner_input(scan_data)
            else:
                self.scan_stats['invalid_scans'] += 1
                self.last_scan_display.configure(
                    text=f"Invalid scan: {message}",
                    text_color="red"
                )
                self.root.after(2000, self.reset_scan_display)
    
    def process_scanner_input(self, scan_data):
        """Process scanned barcode/QR code data"""
        current_time = time.time()
        
        # Check scanning cooldown
        if current_time - self.last_scan_time < self.scan_cooldown:
            cooldown_remaining = self.scan_cooldown - (current_time - self.last_scan_time)
            print(f"[SCAN DEBUG] Scan cooldown active ({cooldown_remaining:.1f}s remaining)")
            self.last_scan_display.configure(
                text=f"Cooldown active ({cooldown_remaining:.1f}s)",
                text_color="orange"
            )
            self.root.after(2000, self.reset_scan_display)
            return
        
        print(f"[SCAN DEBUG] Processing scan: '{scan_data}'")
        
        # Update scan display
        self.last_scan_display.configure(
            text=f"Scanned: {scan_data}",
            text_color="cyan"
        )
        
        # Look up employee
        employee = self.db.get_employee(scan_data)
        if employee:
            print(f"[SCAN DEBUG] Found employee: {employee['name']} ({employee['employee_id']})")
            
            # Toggle attendance
            success, message = self.attendance_manager.toggle_attendance(
                scan_data, "qr_code"
            )
            
            if success:
                self.scan_stats['successful_scans'] += 1
                print(f"[SCAN DEBUG] Attendance success: {message}")
                self.show_success_message(f"✓ {employee['name']} - {message}")
                self.last_scan_time = current_time  # Update cooldown timer
                self.play_beep(True)  # Success beep
            else:
                self.scan_stats['failed_scans'] += 1
                print(f"[SCAN DEBUG] Attendance failed: {message}")
                self.show_error_message(f"✗ {message}")
                self.play_beep(False)  # Failure beep
        else:
            self.scan_stats['failed_scans'] += 1
            print(f"[SCAN DEBUG] Employee not found in database")
            self.show_error_message(f"✗ Employee {scan_data} not found")
            self.play_beep(False)  # Failure beep
        
        # Update statistics display
        self.update_scanner_stats()
        
        self.root.after(5000, self.reset_scan_display)
    
    def update_scanner_stats(self):
        """Update scanner statistics display"""
        total = self.scan_stats['total_scans']
        successful = self.scan_stats['successful_scans']
        
        if total > 0:
            success_rate = int((successful / total) * 100)
            self.stats_label.configure(
                text=f"Scans: {successful}/{total} ({success_rate}%)",
                text_color="green" if success_rate >= 90 else "orange" if success_rate >= 70 else "red"
            )
        else:
            self.stats_label.configure(text="Scans: 0/0 (100%)", text_color="gray")
    
    def reset_scan_display(self):
        """Reset the scan display to default"""
        self.last_scan_display.configure(
            text="Ready for next scan",
            text_color="gray"
        )
    
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
    
    def show_scanner_stats(self):
        """Show detailed scanner statistics"""
        session_time = time.time() - self.scan_stats['session_start']
        hours = int(session_time // 3600)
        minutes = int((session_time % 3600) // 60)
        
        stats_text = (f"SCANNER STATISTICS\n\n" +
                     f"Session Time: {hours:02d}:{minutes:02d}\n" +
                     f"Total Scans: {self.scan_stats['total_scans']}\n" +
                     f"Successful: {self.scan_stats['successful_scans']}\n" +
                     f"Failed: {self.scan_stats['failed_scans']}\n" +
                     f"Invalid: {self.scan_stats['invalid_scans']}\n\n" +
                     f"Success Rate: {int((self.scan_stats['successful_scans'] / max(1, self.scan_stats['total_scans'])) * 100)}%\n" +
                     f"Scans/Hour: {int(self.scan_stats['total_scans'] / max(1, session_time / 3600))}")
        
        self.message_frame.pack(fill="x", padx=30, pady=10)
        self.message_label.configure(text=stats_text, text_color="cyan")
        self.status_label.configure(text="● SCANNER STATISTICS", text_color="cyan")
        
        # Auto-clear after 8 seconds
        self.root.after(8000, self.clear_message)
    
    def show_help(self):
        """Show help message"""
        help_text = ("SCANNER KIOSK ATTENDANCE SYSTEM\n\n" +
                    "● Scan your employee barcode/QR code\n" +
                    "● Or enter your Employee ID manually\n\n" +
                    "CONTROLS:\n" +
                    "• Enter = Manual Entry\n" +
                    "• F1 = Show Help\n" +
                    "• F2 = Scanner Statistics\n" +
                    "• F3 = Employee Lookup\n" +
                    "• F4 = Toggle Fullscreen\n" +
                    "• - = Exit (with confirmation)\n" +
                    "• ESC = Clear Messages")
        
        self.message_frame.pack(fill="x", padx=30, pady=10)
        self.message_label.configure(text=help_text, text_color="cyan")
        self.status_label.configure(text="● HELP DISPLAYED", text_color="cyan")
        
        # Auto-clear after 10 seconds
        self.root.after(10000, self.clear_message)
    
    def show_employee_lookup(self):
        """Show employee lookup information"""
        employees = self.db.get_all_employees()
        
        if not employees:
            lookup_text = "EMPLOYEE LOOKUP\n\nNo employees found in database"
        else:
            lookup_text = "EMPLOYEE LOOKUP\n\nRegistered Employees:\n"
            for emp in employees[:10]:  # Show first 10 employees
                lookup_text += f"• {emp['employee_id']}: {emp['name']}\n"
            
            if len(employees) > 10:
                lookup_text += f"... and {len(employees) - 10} more"
        
        self.message_frame.pack(fill="x", padx=30, pady=10)
        self.message_label.configure(text=lookup_text, text_color="cyan")
        self.status_label.configure(text="● EMPLOYEE LOOKUP", text_color="cyan")
        
        # Auto-clear after 8 seconds
        self.root.after(8000, self.clear_message)
    
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
        
        entry = tk.Entry(dialog, font=("Arial", 14), width=20, justify="center")
        entry.pack(pady=10)
        entry.focus_set()
        
        def submit():
            employee_id = entry.get().strip()
            dialog.destroy()
            if employee_id:
                self.process_manual_entry(employee_id)
        
        def cancel():
            dialog.destroy()
        
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
    
    def process_manual_entry(self, employee_id):
        """Process manual employee ID entry"""
        current_time = time.time()
        
        # Check scanning cooldown
        if current_time - self.last_scan_time < self.scan_cooldown:
            cooldown_remaining = self.scan_cooldown - (current_time - self.last_scan_time)
            self.show_error_message(f"✗ Please wait {cooldown_remaining:.1f} seconds")
            return
        
        employee = self.db.get_employee(employee_id)
        if employee:
            success, message = self.attendance_manager.toggle_attendance(employee_id, "manual")
            if success:
                self.show_success_message(f"✓ {employee['name']} - {message}")
                self.last_scan_time = current_time  # Update cooldown timer
            else:
                self.show_error_message(f"✗ {message}")
        else:
            self.show_error_message(f"✗ Employee {employee_id} not found")
    
    def show_success_message(self, message):
        """Show success message"""
        self.message_frame.pack(fill="x", padx=30, pady=10)
        self.message_label.configure(text=message, text_color="green")
        self.status_label.configure(text="● SUCCESS", text_color="green")
        self.root.after(self.auto_timeout * 1000, self.clear_message)
        
        # Update attendance history immediately
        self.update_attendance_history()
    
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
            text="● READY - Please scan your employee barcode/QR code",
            text_color="green"
        )
    
    def update_attendance_history(self):
        """Update the attendance history display"""
        # Clear existing history
        for widget in self.history_frame.winfo_children():
            widget.destroy()
        
        # Get today's attendance with explicit date check
        attendance_records = self.db.get_attendance_today()
        
        # Debug: Show what date we're filtering for
        current_date = datetime.now().strftime("%Y-%m-%d")
        print(f"[ATTENDANCE DEBUG] Looking for records on: {current_date}")
        print(f"[ATTENDANCE DEBUG] Found {len(attendance_records)} records")
        
        # Additional filtering to ensure only today's records
        today_records = []
        for record in attendance_records:
            record_date = record['timestamp'][:10]  # Extract YYYY-MM-DD part
            if record_date == current_date:
                today_records.append(record)
            else:
                print(f"[ATTENDANCE DEBUG] Filtering out record from {record_date}: {record['name']}")
        
        print(f"[ATTENDANCE DEBUG] After date filtering: {len(today_records)} records")
        
        if not today_records:
            no_records_label = ctk.CTkLabel(
                self.history_frame,
                text=f"No attendance records for {current_date}",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            no_records_label.pack(pady=10)
            return
        
        # Group records by employee and keep all records (not just latest)
        employee_records = {}
        for record in today_records:  # Use filtered records
            emp_id = record['employee_id']
            if emp_id not in employee_records:
                employee_records[emp_id] = {
                    'name': record['name'],
                    'records': []
                }
            employee_records[emp_id]['records'].append(record)
        
        # Sort records by time for each employee
        for emp_id in employee_records:
            employee_records[emp_id]['records'].sort(key=lambda x: x['timestamp'])
        
        # Display all records for each employee
        for emp_id, data in employee_records.items():
            self.create_employee_history_section(emp_id, data)
    
    def create_employee_history_section(self, employee_id, data):
        """Create a section showing all attendance records for one employee"""
        # Main frame for this employee - more compact
        main_frame = ctk.CTkFrame(self.history_frame, border_width=2, border_color="gray")
        main_frame.pack(fill="x", padx=5, pady=5)
        
        # Employee header - more compact
        header_frame = ctk.CTkFrame(main_frame)
        header_frame.pack(fill="x", padx=8, pady=8)
        
        # Employee name and ID - slightly smaller fonts for more space
        name_label = ctk.CTkLabel(
            header_frame,
            text=f"{data['name']} (ID: {employee_id})",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w"
        )
        name_label.pack(fill="x", padx=10, pady=3)
        
        # Current status (based on last record)
        last_record = data['records'][-1]  # Most recent record
        current_status = "CHECKED IN" if last_record['status'] == 'in' else "CHECKED OUT"
        status_color = "green" if last_record['status'] == 'in' else "orange"
        status_icon = "🟢" if last_record['status'] == 'in' else "🟠"
        
        status_label = ctk.CTkLabel(
            header_frame,
            text=f"{status_icon} {current_status}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=status_color,
            anchor="w"
        )
        status_label.pack(fill="x", padx=10, pady=(0, 3))
        
        # Records list - more compact
        records_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        records_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        # Show all records for this employee (chronological order)
        for i, record in enumerate(data['records']):
            self.create_single_record_entry(records_frame, record, i)
    
    def create_single_record_entry(self, parent, record, index):
        """Create a single attendance record entry"""
        # Record frame with alternating colors for readability - more compact
        bg_color = "gray20" if index % 2 == 0 else "gray25"
        record_frame = ctk.CTkFrame(parent, fg_color=bg_color)
        record_frame.pack(fill="x", pady=1)
        
        # Parse timestamp
        record_time = datetime.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
        time_str = record_time.strftime("%H:%M:%S")
        
        # Status indicator
        status_text = "IN" if record['status'] == 'in' else "OUT"
        status_color = "green" if record['status'] == 'in' else "red"
        status_icon = "🔵" if record['status'] == 'in' else "🔴"
        
        # Method indicator
        method_text = {
            'qr_code': 'Scanner', 
            'manual': 'Manual'
        }.get(record['method'], record['method'])
        
        # Create horizontal layout - more compact
        info_frame = ctk.CTkFrame(record_frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=5)
        
        # Time (left) - slightly smaller font for more records
        time_label = ctk.CTkLabel(
            info_frame,
            text=time_str,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        time_label.pack(side="left", padx=(0, 15))
        
        # Status (center) - slightly smaller font for more records
        status_label = ctk.CTkLabel(
            info_frame,
            text=f"{status_icon} {status_text}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=status_color,
            anchor="center"
        )
        status_label.pack(side="left", expand=True)
        
        # Method (right) - slightly smaller font for more records
        method_label = ctk.CTkLabel(
            info_frame,
            text=method_text,
            font=ctk.CTkFont(size=14),
            text_color="gray",
            anchor="e"
        )
        method_label.pack(side="right", padx=(15, 0))
    
    def update_loop(self):
        """Main update loop"""
        # Update time
        current_time = datetime.now().strftime("%A, %B %d, %Y - %H:%M:%S")
        self.time_label.configure(text=current_time)
        
        # Update scanning status
        self.update_scanning_status()
        
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
        
        # Schedule next update
        self.root.after(100, self.update_loop)
    
    def update_scanning_status(self):
        """Update the scanning status display"""
        current_time = time.time()
        cooldown_remaining = max(0, self.scan_cooldown - (current_time - self.last_scan_time))
        
        if cooldown_remaining > 0:
            self.mode_label.configure(
                text=f"SCAN COOLDOWN ({cooldown_remaining:.1f}s)",
                text_color="orange"
            )
        else:
            self.mode_label.configure(
                text="SCANNER READY",
                text_color="green"
            )
    
    def quit_app(self):
        """Quit application with confirmation"""
        print("[QUIT DEBUG] Quit requested - showing confirmation")
        
        # Create a full-screen overlay for confirmation
        self.quit_overlay = ctk.CTkToplevel(self.root)
        self.quit_overlay.title("Confirm Exit")
        self.quit_overlay.attributes('-fullscreen', True)
        self.quit_overlay.attributes('-topmost', True)
        self.quit_overlay.configure(fg_color=("gray10", "gray10"))
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
            text="⚠️CONFIRM EXIT",
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
        
        self.quit_overlay.bind('<KP_Subtract>', lambda e: self.confirm_quit())
        self.quit_overlay.bind('<minus>', lambda e: self.confirm_quit())
        self.quit_overlay.bind('<Return>', lambda e: self.cancel_quit())
        self.quit_overlay.bind('<KP_Enter>', lambda e: self.cancel_quit())
        self.quit_overlay.bind('<Escape>', lambda e: self.cancel_quit())
        
        # Focus on overlay to capture keys
        self.quit_overlay.focus_set()
        
        # Auto-cancel after 5 seconds
        self.root.after(5000, self.cancel_quit)
    
    def confirm_quit(self):
        """Actually quit the application"""
        print("[QUIT DEBUG] Quit confirmed - exiting application")
        if hasattr(self, 'quit_overlay') and self.quit_overlay:
            self.quit_overlay.destroy()
        self.root.quit()
        self.root.destroy()
    
    def cancel_quit(self):
        """Cancel the quit operation"""
        print("[QUIT DEBUG] Quit canceled - returning to normal operation")
        if hasattr(self, 'quit_overlay') and self.quit_overlay:
            self.quit_overlay.destroy()
            self.quit_overlay = None
        self.setup_keyboard_shortcuts()

def main():
    """Run the scanner kiosk application"""
    app = ScannerKioskApp()
    try:
        app.root.mainloop()
    except KeyboardInterrupt:
        app.quit_app()

if __name__ == "__main__":
    main()
