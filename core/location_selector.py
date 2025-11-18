"""
Location Selector GUI for checkout location selection
Provides search interface with favorites, recent, and popular locations
"""

import tkinter as tk
import customtkinter as ctk
from typing import Dict, List, Optional, Callable
import threading
from .location_manager import LocationManager

class LocationSelector:
    def __init__(self, parent, nric: str, callback: Callable[[Dict], None]):
        self.parent = parent
        self.nric = nric
        self.callback = callback
        self.location_manager = LocationManager()
        self.selected_location = None
        
        # Search state
        self.search_results = []
        self.search_thread = None
        self.search_delay_timer = None
        
        # Emergency clock-out state
        self.is_emergency_clockout = False
        self.emergency_reason = ""
        
        # Checkout type state
        self.checkout_type = "work"  # Default to "work"
        
        self.create_dialog()
    
    def create_dialog(self):
        """Create the location selection dialog"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Select Checkout Location")
        self.dialog.geometry("800x700")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 450,
            self.parent.winfo_rooty() + 100
        ))
        
        # Configure grid weights for responsive design
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(1, weight=1)
        
        # Handle window close event (X button)
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel_selection)
        
        self.create_header()
        self.create_main_content()
        self.create_footer()
        
        # Load initial data
        self.load_initial_content()
        
        # Focus on search entry
        self.search_entry.focus_set()
    
    def create_header(self):
        """Create dialog header with title and search"""
        header_frame = ctk.CTkFrame(self.dialog)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="🗺️ Where are you going?",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(10, 20))
        
        # Search label
        search_label = ctk.CTkLabel(
            header_frame,
            text="Search Location:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        search_label.grid(row=1, column=0, sticky="w", padx=(10, 10), pady=5)
        
        # Search entry
        self.search_entry = ctk.CTkEntry(
            header_frame,
            placeholder_text="Type place name, address, or business...",
            font=ctk.CTkFont(size=14),
            height=40
        )
        self.search_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=5)
        self.search_entry.bind('<KeyRelease>', self.on_search_changed)
        self.search_entry.bind('<Return>', self.on_search_enter)
        
        # Search button
        self.search_btn = ctk.CTkButton(
            header_frame,
            text="🔍 Search",
            width=100,
            height=40,
            command=self.perform_search
        )
        self.search_btn.grid(row=1, column=2, padx=(10, 10), pady=5)
    
    def create_main_content(self):
        """Create main content area with simplified tabs"""
        # Create main frame
        self.main_frame = ctk.CTkFrame(self.dialog)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Tab buttons - Search Results, Manual Input, and Emergency Clock-Out
        tab_frame = ctk.CTkFrame(self.main_frame)
        tab_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.search_results_btn = ctk.CTkButton(
            tab_frame,
            text="Search Results",
            command=lambda: self.switch_tab("search"),
            width=140
        )
        self.search_results_btn.pack(side="left", padx=5)
        
        self.manual_input_btn = ctk.CTkButton(
            tab_frame,
            text="Manual Input",
            command=lambda: self.switch_tab("manual"),
            width=140
        )
        self.manual_input_btn.pack(side="left", padx=5)
        
        self.emergency_btn = ctk.CTkButton(
            tab_frame,
            text="🚨 EMERGENCY CLOCK-OUT",
            command=lambda: self.switch_tab("emergency"),
            width=200,
            fg_color=("orange", "darkorange"),
            hover_color=("red", "darkred")
        )
        self.emergency_btn.pack(side="left", padx=5)
        
        # Content area
        self.content_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Current tab
        self.current_tab = "search"
        self.switch_tab("search")
    
    def create_footer(self):
        """Create dialog footer with action buttons"""
        footer_frame = ctk.CTkFrame(self.dialog)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        # Configure footer frame grid weights to ensure proper layout
        footer_frame.grid_columnconfigure(0, weight=1)  # Selection area takes available space
        footer_frame.grid_columnconfigure(1, weight=0)  # Button area fixed width
        
        # Selected location display with limited width
        selection_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        selection_frame.grid(row=0, column=0, sticky="ew", padx=(20, 10), pady=15)
        
        self.selection_label = ctk.CTkLabel(
            selection_frame,
            text="No location selected",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
            width=400  # Limit width to prevent overflow
        )
        self.selection_label.pack(fill="x", expand=True)
        
        # Action buttons - fixed position on right
        button_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e", padx=(10, 20), pady=15)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.cancel_selection,
            width=100,
            fg_color="gray"
        )
        cancel_btn.pack(side="left", padx=5)
        
        self.confirm_btn = ctk.CTkButton(
            button_frame,
            text="Confirm Location",
            command=self.confirm_selection,
            width=150,
            state="disabled"
        )
        self.confirm_btn.pack(side="left", padx=5)
    
    def switch_tab(self, tab_name: str):
        """Switch between different tabs"""
        self.current_tab = tab_name
        
        # Update button colors
        buttons = {
            "search": self.search_results_btn,
            "manual": self.manual_input_btn,
            "emergency": self.emergency_btn
        }
        
        for name, btn in buttons.items():
            if name == tab_name:
                if name == "emergency":
                    btn.configure(fg_color=("red", "darkred"))
                else:
                    btn.configure(fg_color=("blue", "darkblue"))
            else:
                if name == "emergency":
                    btn.configure(fg_color=("orange", "darkorange"))
                else:
                    btn.configure(fg_color=("gray70", "gray30"))
        
        # Load content for selected tab
        if tab_name == "search":
            self.display_search_results()
        elif tab_name == "manual":
            self.show_manual_input()
        elif tab_name == "emergency":
            self.show_emergency_clockout()
    
    def load_initial_content(self):
        """Load initial content (search instructions)"""
        self.show_search_instructions()
    
    def show_search_instructions(self):
        """Show search instructions when no search has been performed"""
        self.clear_content()
        
        # Instructions frame
        instructions_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        instructions_frame.pack(fill="x", padx=20, pady=30)
        
        # Icon and title
        icon_label = ctk.CTkLabel(
            instructions_frame,
            text="🔍",
            font=ctk.CTkFont(size=48)
        )
        icon_label.pack(pady=(0, 10))
        
        title_label = ctk.CTkLabel(
            instructions_frame,
            text="Search for Your Location",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Instructions
        instructions_text = """Type in the search box above to find your location:
        
• Business names (e.g., "KLCC", "Sunway Pyramid")
• Addresses (e.g., "Jalan Bukit Bintang")
• Areas (e.g., "Mont Kiara", "Bangsar")
• Landmarks (e.g., "Twin Towers", "KL Sentral")

Or switch to Manual Input to type your location directly."""
        
        instructions_label = ctk.CTkLabel(
            instructions_frame,
            text=instructions_text,
            font=ctk.CTkFont(size=14),
            justify="left"
        )
        instructions_label.pack(pady=10)
    
    def show_manual_input(self):
        """Show manual input interface"""
        self.clear_content()
        
        # Manual input frame
        manual_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        manual_frame.pack(fill="x", padx=20, pady=30)
        
        # Title
        title_label = ctk.CTkLabel(
            manual_frame,
            text="✏️ Enter Location Manually",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Manual location input
        location_label = ctk.CTkLabel(
            manual_frame,
            text="Location Name:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        location_label.pack(fill="x", pady=(0, 5))
        
        self.manual_location_entry = ctk.CTkEntry(
            manual_frame,
            placeholder_text="Enter location name (e.g., Client Office, Home, Site Visit)",
            font=ctk.CTkFont(size=14),
            height=40
        )
        self.manual_location_entry.pack(fill="x", pady=(0, 15))
        self.manual_location_entry.bind('<KeyRelease>', self.on_manual_input_changed)
        
        # Optional address input
        address_label = ctk.CTkLabel(
            manual_frame,
            text="Address (Optional):",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        address_label.pack(fill="x", pady=(0, 5))
        
        self.manual_address_entry = ctk.CTkEntry(
            manual_frame,
            placeholder_text="Enter address or description (optional)",
            font=ctk.CTkFont(size=14),
            height=40
        )
        self.manual_address_entry.pack(fill="x", pady=(0, 20))
        self.manual_address_entry.bind('<KeyRelease>', self.on_manual_input_changed)
        
        # Checkout type selection
        type_label = ctk.CTkLabel(
            manual_frame,
            text="Checkout Type:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        type_label.pack(fill="x", pady=(10, 5))
        
        type_container = ctk.CTkFrame(manual_frame, fg_color="transparent")
        type_container.pack(fill="x", pady=(0, 10))
        
        self.checkout_type_var = tk.StringVar(value="work")
        
        work_radio = ctk.CTkRadioButton(
            type_container,
            text="Work",
            variable=self.checkout_type_var,
            value="work",
            font=ctk.CTkFont(size=15)
        )
        work_radio.pack(side="left", padx=(0, 20))
        
        personal_radio = ctk.CTkRadioButton(
            type_container,
            text="Personal",
            variable=self.checkout_type_var,
            value="personal",
            font=ctk.CTkFont(size=15)
        )
        personal_radio.pack(side="left")
        
        # Example text
        example_label = ctk.CTkLabel(
            manual_frame,
            text="Examples: 'Client Meeting', 'Site Inspection', 'Home Office', 'Field Work'",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        example_label.pack(pady=(10, 0))
    
    def on_manual_input_changed(self, event):
        """Handle manual input changes"""
        location_name = self.manual_location_entry.get().strip()
        
        # Enable/disable use button based on input
        if len(location_name) >= 2:
            self.confirm_btn.configure(state="normal", fg_color=("green", "darkgreen"))
            
            # Auto-select manual location
            address = self.manual_address_entry.get().strip()
            manual_location = {
                'name': location_name,
                'address': address if address else location_name,
                'latitude': None,
                'longitude': None,
                'manual_input': True
            }
            self.select_location(manual_location)
        else:
            # Clear selection if input is too short
            self.selected_location = None
            self.selection_label.configure(text="No location selected", text_color="gray")
            self.confirm_btn.configure(state="disabled", fg_color=("gray70", "gray30"))
    
    def use_manual_location(self):
        """Use manually entered location"""
        location_name = self.manual_location_entry.get().strip()
        address = self.manual_address_entry.get().strip()
        
        if len(location_name) >= 2:
            manual_location = {
                'name': location_name,
                'address': address if address else location_name,
                'latitude': None,
                'longitude': None,
                'manual_input': True
            }
            
            self.selected_location = manual_location
            self.confirm_selection()
    
    def show_emergency_clockout(self):
        """Show emergency clock-out interface"""
        self.clear_content()
        
        # Emergency frame
        emergency_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        emergency_frame.pack(fill="x", padx=20, pady=30)
        
        # Warning icon and title
        title_label = ctk.CTkLabel(
            emergency_frame,
            text="🚨 EMERGENCY CLOCK-OUT",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="red"
        )
        title_label.pack(pady=(0, 10))
        
        # Warning message
        warning_label = ctk.CTkLabel(
            emergency_frame,
            text="⚠️ This will immediately CLOCK YOU OUT and end your workday,\neven if you haven't reached the standard clock-out time.",
            font=ctk.CTkFont(size=13),
            text_color="orange",
            justify="center"
        )
        warning_label.pack(pady=(0, 20))
        
        # Divider
        divider = ctk.CTkFrame(emergency_frame, height=2, fg_color="gray")
        divider.pack(fill="x", pady=10)
        
        # Location input
        location_label = ctk.CTkLabel(
            emergency_frame,
            text="Where are you going? *",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
            text_color="red"
        )
        location_label.pack(fill="x", pady=(10, 5))
        
        self.emergency_location_entry = ctk.CTkEntry(
            emergency_frame,
            placeholder_text="Enter location (e.g., Hospital, Home, Personal Emergency)",
            font=ctk.CTkFont(size=14),
            height=40
        )
        self.emergency_location_entry.pack(fill="x", pady=(0, 15))
        self.emergency_location_entry.bind('<KeyRelease>', self.on_emergency_input_changed)
        
        # Emergency reason input
        reason_label = ctk.CTkLabel(
            emergency_frame,
            text="Emergency Reason: *",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
            text_color="red"
        )
        reason_label.pack(fill="x", pady=(0, 5))
        
        self.emergency_reason_entry = ctk.CTkTextbox(
            emergency_frame,
            height=100,
            font=ctk.CTkFont(size=13)
        )
        self.emergency_reason_entry.pack(fill="x", pady=(0, 15))
        self.emergency_reason_entry.bind('<KeyRelease>', self.on_emergency_input_changed)
        
        # Helper text
        helper_label = ctk.CTkLabel(
            emergency_frame,
            text="Please provide a brief explanation of your emergency situation.\nExample: 'Family emergency', 'Medical appointment', 'Personal urgent matter'",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        helper_label.pack(pady=(0, 20))
        
        # Important notice
        notice_frame = ctk.CTkFrame(emergency_frame, fg_color=("yellow", "orange"))
        notice_frame.pack(fill="x", pady=10)
        
        notice_label = ctk.CTkLabel(
            notice_frame,
            text="⚠️ IMPORTANT: This emergency clock-out will be logged and may require\nmanager review. Use only for genuine emergencies.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="black",
            justify="center"
        )
        notice_label.pack(padx=15, pady=15)
    
    def on_emergency_input_changed(self, event):
        """Handle emergency input changes"""
        location = self.emergency_location_entry.get().strip()
        reason = self.emergency_reason_entry.get("1.0", "end-1c").strip()
        
        # Enable confirm button if both fields are filled
        if len(location) >= 3 and len(reason) >= 5:
            self.is_emergency_clockout = True
            self.emergency_reason = reason
            
            # Auto-select emergency location
            emergency_location = {
                'name': location,
                'address': location,
                'latitude': None,
                'longitude': None,
                'emergency': True,
                'emergency_reason': reason
            }
            self.select_location(emergency_location)
            
            # Update confirm button text for emergency
            self.confirm_btn.configure(
                text="⚠️ Confirm Emergency Clock-Out",
                state="normal",
                fg_color=("red", "darkred")
            )
        else:
            # Reset if inputs are insufficient
            self.is_emergency_clockout = False
            self.emergency_reason = ""
            self.selected_location = None
            self.selection_label.configure(text="Please fill in all required fields", text_color="orange")
            self.confirm_btn.configure(
                text="Confirm Location",
                state="disabled",
                fg_color=("gray70", "gray30")
            )
    
    def on_search_changed(self, event):
        """Handle search text changes with debouncing"""
        # Cancel previous timer
        if self.search_delay_timer:
            self.dialog.after_cancel(self.search_delay_timer)
        
        # Set new timer for delayed search
        self.search_delay_timer = self.dialog.after(500, self.perform_search)
    
    def on_search_enter(self, event):
        """Handle Enter key in search"""
        self.perform_search()
    
    def perform_search(self):
        """Perform location search"""
        query = self.search_entry.get().strip()
        
        if len(query) < 2:
            return
        
        # Cancel any existing search
        if self.search_thread and self.search_thread.is_alive():
            return
        
        # Switch to search results tab
        self.switch_tab("search")
        self.clear_content()
        
        # Show loading
        loading_label = ctk.CTkLabel(
            self.content_frame,
            text=f"Searching for '{query}'...",
            font=ctk.CTkFont(size=14)
        )
        loading_label.pack(pady=20)
        
        # Search in background
        def search_thread():
            try:
                results = self.location_manager.search_locations(query, limit=15)
                self.search_results = results
                self.dialog.after(0, lambda: self.display_search_results())
            except Exception as e:
                print(f"[LOCATION DEBUG] Search error: {e}")
                self.dialog.after(0, lambda: self.show_search_error())
        
        self.search_thread = threading.Thread(target=search_thread, daemon=True)
        self.search_thread.start()
    
    def display_search_results(self):
        """Display search results"""
        if not hasattr(self, 'search_results') or not self.search_results:
            self.show_search_instructions()
            return
        self.display_locations(self.search_results, "search")
    
    def show_search_error(self):
        """Show search error message"""
        self.clear_content()
        error_label = ctk.CTkLabel(
            self.content_frame,
            text="❌ Search failed. Please check your internet connection.",
            font=ctk.CTkFont(size=14),
            text_color="red"
        )
        error_label.pack(pady=20)
    
    def display_locations(self, locations: List[Dict], tab_type: str):
        """Display list of locations"""
        self.clear_content()
        
        if not locations:
            no_results_msg = {
                "search": "No locations found.\nTry a different search term or use Manual Input tab."
            }
            
            no_results_label = ctk.CTkLabel(
                self.content_frame,
                text=no_results_msg.get(tab_type, "No locations found."),
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_results_label.pack(pady=30)
            return
        
        # Add checkout type selection at the top for search results
        type_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        type_frame.pack(fill="x", padx=20, pady=(10, 15))
        
        type_label = ctk.CTkLabel(
            type_frame,
            text="Checkout Type:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        type_label.pack(side="left", padx=(0, 15))
        
        self.checkout_type_var = tk.StringVar(value="work")
        
        work_radio = ctk.CTkRadioButton(
            type_frame,
            text="Work",
            variable=self.checkout_type_var,
            value="work",
            font=ctk.CTkFont(size=13)
        )
        work_radio.pack(side="left", padx=(0, 15))
        
        personal_radio = ctk.CTkRadioButton(
            type_frame,
            text="Personal",
            variable=self.checkout_type_var,
            value="personal",
            font=ctk.CTkFont(size=13)
        )
        personal_radio.pack(side="left")
        
        # Divider
        divider = ctk.CTkFrame(self.content_frame, height=2, fg_color="gray")
        divider.pack(fill="x", padx=20, pady=(0, 10))
        
        # Display locations
        for i, location in enumerate(locations):
            self.create_location_item(location, i)
    
    def create_location_item(self, location: Dict, index: int):
        """Create a clickable location item"""
        # Main frame for location item
        item_frame = ctk.CTkFrame(self.content_frame)
        item_frame.pack(fill="x", padx=10, pady=5)
        
        # Make frame clickable
        item_frame.bind("<Button-1>", lambda e: self.select_location(location))
        
        # Location content
        content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=10)
        content_frame.bind("<Button-1>", lambda e: self.select_location(location))
        
        # Location name
        name_label = ctk.CTkLabel(
            content_frame,
            text=f"📍 {location.get('name', 'Unknown Location')}",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(fill="x")
        name_label.bind("<Button-1>", lambda e: self.select_location(location))
        
        # Location address
        if location.get('address'):
            address_label = ctk.CTkLabel(
                content_frame,
                text=location['address'],
                font=ctk.CTkFont(size=12),
                text_color="gray",
                anchor="w"
            )
            address_label.pack(fill="x", pady=(2, 0))
            address_label.bind("<Button-1>", lambda e: self.select_location(location))
        
        # Additional info (only for search results with useful data)
        info_parts = []
        if location.get('use_count', 0) > 1:
            info_parts.append(f"Used {location['use_count']} times")
        if location.get('manual_input'):
            info_parts.append("✏️ Manual Input")
        
        if info_parts:
            info_label = ctk.CTkLabel(
                content_frame,
                text=" • ".join(info_parts),
                font=ctk.CTkFont(size=10),
                text_color="blue",
                anchor="w"
            )
            info_label.pack(fill="x", pady=(2, 0))
            info_label.bind("<Button-1>", lambda e: self.select_location(location))
    
    def select_location(self, location: Dict):
        """Select a location"""
        self.selected_location = location
        
        # Update selection display with proper truncation
        name = location.get('name', 'Unknown')
        address = location.get('address', '')
        
        # Truncate name if too long
        if len(name) > 30:
            name = name[:30] + "..."
            
        # Truncate address more aggressively for footer display
        if len(address) > 40:
            address = address[:40] + "..."
        
        # Build selection text with total character limit
        selection_text = f"Selected: {name}"
        if address:
            selection_text += f" ({address})"
            
        # Final truncation if still too long (safeguard)
        if len(selection_text) > 70:
            selection_text = selection_text[:67] + "..."
        
        self.selection_label.configure(
            text=selection_text,
            text_color="green"
        )
        
        # Enable confirm button
        self.confirm_btn.configure(state="normal", fg_color=("green", "darkgreen"))
        
        print(f"[LOCATION DEBUG] Selected location: {name}")
    
    def clear_content(self):
        """Clear content area"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def confirm_selection(self):
        """Confirm location selection"""
        if self.selected_location:
            # Add checkout type to location data
            self.selected_location['type'] = self.checkout_type_var.get()
            
            # Add emergency flag to location data if this is emergency clock-out
            if self.is_emergency_clockout:
                self.selected_location['emergency_clockout'] = True
                self.selected_location['emergency_reason'] = self.emergency_reason
                print(f"[EMERGENCY DEBUG] Emergency clock-out confirmed: {self.selected_location['name']}, Reason: {self.emergency_reason}")
            
            print(f"[CHECKOUT DEBUG] Checkout type selected: {self.selected_location['type']}")
            self.callback(self.selected_location)
            self.dialog.destroy()
    
    def cancel_selection(self):
        """Cancel location selection"""
        print("[LOCATION DEBUG] Location selection cancelled")
        # Call callback with None to indicate cancellation
        self.callback(None)
        self.dialog.destroy()
