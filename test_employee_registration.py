#!/usr/bin/env python3
"""
Test script for employee registration feature
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import tkinter as tk
from simple_kiosk import SimpleKioskApp
from core.mongodb_manager import MongoDBManager

def test_employee_registration():
    """Test the new employee registration feature"""
    
    # Create a test window
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    try:
        # Initialize database connection
        db = MongoDBManager()
        
        # Create kiosk instance
        kiosk = SimpleKioskApp()
        
        print("📋 Testing Employee Registration Feature...")
        print("🔧 Features to test:")
        print("   • Employee registration dialog (press R or click button)")
        print("   • Form validation (employee ID, name, department)")
        print("   • Face capture process (12 captures over 4 seconds)")
        print("   • Face vector averaging and database storage")
        print("   • Integration with existing face recognition system")
        print("")
        print("🎯 Instructions:")
        print("   1. Wait for the kiosk to fully load")
        print("   2. Press 'R' key or click 'Register New Employee' button")
        print("   3. Fill in employee details")
        print("   4. Click 'Start Face Capture' and look at camera")
        print("   5. System will capture 12 face vectors over 4 seconds")
        print("   6. Employee will be saved to database with averaged vector")
        print("")
        
        # Keep the application open
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    test_employee_registration()
