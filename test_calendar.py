#!/usr/bin/env python3
"""
Test script to demonstrate the new calendar-based date picker
"""

import tkinter as tk
from datetime import datetime

try:
    from tkcalendar import Calendar
    print("✅ tkcalendar module is available")
except ImportError:
    print("❌ tkcalendar module not found")
    exit(1)

def create_test_calendar():
    """Create a test window with calendar"""
    root = tk.Tk()
    root.title("Calendar Date Picker Test")
    root.geometry("800x600")
    root.configure(bg='#f0f8ff')
    
    # Title
    title = tk.Label(root, text="📅 Calendar Date Picker Test", 
                    font=("Arial", 16, "bold"), bg='#f0f8ff', fg='#2E86C1')
    title.pack(pady=20)
    
    # Calendar widget
    cal_frame = tk.LabelFrame(root, text="Select Date", font=("Arial", 12, "bold"),
                             bg='#f0f8ff', fg='#2E86C1', padx=10, pady=10)
    cal_frame.pack(pady=20)
    
    today = datetime.now()
    cal = Calendar(
        cal_frame,
        selectmode='day',
        year=today.year,
        month=today.month,
        day=today.day,
        background='white',
        foreground='black',
        bordercolor='#2E86C1',
        headersbackground='#2E86C1',
        headersforeground='white',
        selectbackground='#87CEEB',
        selectforeground='black',
        weekendbackground='#f0f8ff',
        weekendforeground='black',
        othermonthforeground='gray',
        othermonthbackground='#f5f5f5',
        font=('Arial', 11)
    )
    cal.pack(pady=10)
    
    # Selected date display
    date_label = tk.Label(root, text="Selected Date: None", 
                         font=("Arial", 12), bg='#f0f8ff')
    date_label.pack(pady=10)
    
    def show_selected_date():
        selected = cal.selection_get()
        date_label.config(text=f"Selected Date: {selected.strftime('%Y-%m-%d (%A)')}")
    
    # Buttons
    button_frame = tk.Frame(root, bg='#f0f8ff')
    button_frame.pack(pady=20)
    
    get_date_btn = tk.Button(button_frame, text="📅 Get Selected Date", 
                            font=("Arial", 11, "bold"), command=show_selected_date,
                            bg='#2E86C1', fg='white', relief='raised', bd=2)
    get_date_btn.pack(side="left", padx=10)
    
    today_btn = tk.Button(button_frame, text="📅 Today", 
                         font=("Arial", 11, "bold"), 
                         command=lambda: cal.selection_set(datetime.now().date()),
                         bg='#87CEEB', fg='black', relief='raised', bd=2)
    today_btn.pack(side="left", padx=10)
    
    close_btn = tk.Button(button_frame, text="❌ Close", 
                         font=("Arial", 11), command=root.quit,
                         bg='#ff6b6b', fg='white', relief='raised', bd=2)
    close_btn.pack(side="left", padx=10)
    
    print("✅ Calendar test window created successfully")
    print("📋 Features:")
    print("   - Click on any date to select it")
    print("   - Use 'Get Selected Date' to see the selected date")
    print("   - Use 'Today' button to jump to current date")
    print("   - Navigate between months using arrow buttons")
    
    root.mainloop()

if __name__ == "__main__":
    print("🚀 Starting calendar date picker test...")
    create_test_calendar()
