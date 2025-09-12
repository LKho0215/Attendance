#!/usr/bin/env python3
"""
Test script for face and QR recognition confirmation dialogs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
import tkinter as tk
from core.mongodb_manager import MongoDBManager

class ConfirmationDialogTest:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Test Confirmation Dialogs")
        self.root.geometry("400x300")
        
        # Initialize database
        try:
            self.db = MongoDBManager()
            print("✓ Database connected successfully")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return
        
        # Mock variables for testing
        self.camera_paused = False
        
        # Create test buttons
        self.create_test_interface()
        
    def create_test_interface(self):
        """Create test interface"""
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            main_frame,
            text="Confirmation Dialog Test",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Test face recognition button
        face_button = ctk.CTkButton(
            main_frame,
            text="Test Face Recognition Dialog",
            command=self.test_face_dialog,
            height=40
        )
        face_button.pack(pady=10)
        
        # Test QR recognition button
        qr_button = ctk.CTkButton(
            main_frame,
            text="Test QR Code Dialog",
            command=self.test_qr_dialog,
            height=40
        )
        qr_button.pack(pady=10)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Click buttons above to test dialogs",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=20)
        
    def test_face_dialog(self):
        """Test face recognition confirmation dialog"""
        # Mock face data
        face = {
            'name': 'Test Employee',
            'employee_id': 'EMP001',
            'confidence': '85.4%'
        }
        
        # Mock employee data
        employee = {
            'name': 'Test Employee',
            'employee_id': 'EMP001'
        }
        
        print("Testing face recognition dialog...")
        self.show_face_recognition_confirmation(face, employee)
        
    def test_qr_dialog(self):
        """Test QR code confirmation dialog"""
        # Mock QR code data
        qr_code = {
            'data': 'EMP001',
            'employee_id': 'EMP001'
        }
        
        # Mock employee data
        employee = {
            'name': 'Test Employee',
            'employee_id': 'EMP001'
        }
        
        print("Testing QR code dialog...")
        self.show_qr_recognition_confirmation(qr_code, employee)
        
    def show_face_recognition_confirmation(self, face, employee):
        """Show confirmation dialog for face recognition"""
        try:
            # Create confirmation dialog
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Confirm Face Recognition")
            dialog.geometry("400x200")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.focus()
            
            # Center the dialog
            dialog.lift()
            dialog.attributes('-topmost', True)
            
            # Main frame
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Message label
            message_text = f"Recognized: {face['name']}\nEmployee ID: {face['employee_id']}"
            message_label = ctk.CTkLabel(
                main_frame,
                text=message_text,
                font=ctk.CTkFont(size=16, weight="bold")
            )
            message_label.pack(pady=10)
            
            # Confidence info
            confidence_text = f"Confidence: {face.get('confidence', 'N/A')}"
            confidence_label = ctk.CTkLabel(
                main_frame,
                text=confidence_text,
                font=ctk.CTkFont(size=12)
            )
            confidence_label.pack(pady=5)
            
            # Question label
            question_label = ctk.CTkLabel(
                main_frame,
                text="Is this recognition correct?",
                font=ctk.CTkFont(size=14)
            )
            question_label.pack(pady=10)
            
            # Button frame
            button_frame = ctk.CTkFrame(main_frame)
            button_frame.pack(pady=10)
            
            # Confirmation result
            confirmation_result = {"confirmed": False}
            
            def confirm_recognition():
                confirmation_result["confirmed"] = True
                self.status_label.configure(text="✓ Face recognition CONFIRMED")
                dialog.destroy()
            
            def reject_recognition():
                confirmation_result["confirmed"] = False
                self.status_label.configure(text="✗ Face recognition REJECTED")
                dialog.destroy()
            
            # Yes button
            yes_button = ctk.CTkButton(
                button_frame,
                text="✓ Yes",
                command=confirm_recognition,
                width=80,
                fg_color="green",
                hover_color="darkgreen"
            )
            yes_button.pack(side="left", padx=(0, 10))
            
            # No button
            no_button = ctk.CTkButton(
                button_frame,
                text="✗ No",
                command=reject_recognition,
                width=80,
                fg_color="red",
                hover_color="darkred"
            )
            no_button.pack(side="left")
            
            # Bind keyboard shortcuts
            dialog.bind('<Return>', lambda e: confirm_recognition())
            dialog.bind('<Escape>', lambda e: reject_recognition())
            dialog.bind('<space>', lambda e: confirm_recognition())
            
            # Auto-focus on Yes button
            yes_button.focus()
                
        except Exception as e:
            print(f"Error in face recognition confirmation: {e}")
            self.status_label.configure(text=f"Error: {e}")

    def show_qr_recognition_confirmation(self, qr_code, employee):
        """Show confirmation dialog for QR code recognition"""
        try:
            # Create confirmation dialog
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Confirm QR Code Recognition")
            dialog.geometry("400x200")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.focus()
            
            # Center the dialog
            dialog.lift()
            dialog.attributes('-topmost', True)
            
            # Main frame
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Message label
            message_text = f"Scanned: {employee['name']}\nEmployee ID: {employee['employee_id']}"
            message_label = ctk.CTkLabel(
                main_frame,
                text=message_text,
                font=ctk.CTkFont(size=16, weight="bold")
            )
            message_label.pack(pady=10)
            
            # QR data info
            qr_data_text = f"QR Data: {qr_code.get('data', 'N/A')}"
            qr_data_label = ctk.CTkLabel(
                main_frame,
                text=qr_data_text,
                font=ctk.CTkFont(size=12)
            )
            qr_data_label.pack(pady=5)
            
            # Question label
            question_label = ctk.CTkLabel(
                main_frame,
                text="Is this scan correct?",
                font=ctk.CTkFont(size=14)
            )
            question_label.pack(pady=10)
            
            # Button frame
            button_frame = ctk.CTkFrame(main_frame)
            button_frame.pack(pady=10)
            
            # Confirmation result
            confirmation_result = {"confirmed": False}
            
            def confirm_recognition():
                confirmation_result["confirmed"] = True
                self.status_label.configure(text="✓ QR code scan CONFIRMED")
                dialog.destroy()
            
            def reject_recognition():
                confirmation_result["confirmed"] = False
                self.status_label.configure(text="✗ QR code scan REJECTED")
                dialog.destroy()
            
            # Yes button
            yes_button = ctk.CTkButton(
                button_frame,
                text="✓ Yes",
                command=confirm_recognition,
                width=80,
                fg_color="green",
                hover_color="darkgreen"
            )
            yes_button.pack(side="left", padx=(0, 10))
            
            # No button
            no_button = ctk.CTkButton(
                button_frame,
                text="✗ No",
                command=reject_recognition,
                width=80,
                fg_color="red",
                hover_color="darkred"
            )
            no_button.pack(side="left")
            
            # Bind keyboard shortcuts
            dialog.bind('<Return>', lambda e: confirm_recognition())
            dialog.bind('<Escape>', lambda e: reject_recognition())
            dialog.bind('<space>', lambda e: confirm_recognition())
            
            # Auto-focus on Yes button
            yes_button.focus()
                
        except Exception as e:
            print(f"Error in QR recognition confirmation: {e}")
            self.status_label.configure(text=f"Error: {e}")
    
    def run(self):
        """Run the test application"""
        self.root.mainloop()

def main():
    """Main function"""
    print("Starting confirmation dialog test...")
    
    # Set appearance mode
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Create and run test
    test_app = ConfirmationDialogTest()
    test_app.run()

if __name__ == "__main__":
    main()
