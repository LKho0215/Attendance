#!/usr/bin/env python3
"""
Test script to demonstrate the improved date picker features
Shows the export dialog with simplified month/year controls and real-time preview
"""

import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from simple_kiosk import AttendanceKiosk

def test_date_picker():
    """Test the enhanced date picker dialog"""
    print("🎯 Testing Enhanced Date Picker Features:")
    print("✅ Calendar widgets for single date and date range selections")
    print("✅ Simplified month/year dropdowns for monthly exports")
    print("✅ Simple year dropdown for yearly exports") 
    print("✅ Real-time preview updates (no manual refresh needed)")
    print("✅ Quick selection buttons for common ranges")
    print()
    print("Opening export dialog... Press Numpad * (asterisk) or use menu to test!")
    
    # Initialize the kiosk (this will setup the database connection)
    app = AttendanceKiosk()
    
    # Show the export dialog directly
    app.show_export_date_selection_dialog()
    
    # Start the GUI event loop
    app.root.mainloop()

if __name__ == "__main__":
    test_date_picker()
