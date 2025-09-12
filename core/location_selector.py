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
    def __init__(self, parent, employee_id: str, callback: Callable[[Dict], None]):
        self.parent = parent
        self.employee_id = employee_id
        self.callback = callback
        self.location_manager = LocationManager()
        self.selected_location = None
        
        # Search state
        self.search_results = []
        self.search_thread = None
        self.search_delay_timer = None
        
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
            self.parent.winfo_rootx() + 200,
            self.parent.winfo_rooty() + 100
        ))
        
        # Configure grid weights for responsive design
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(1, weight=1)
        
        self.create_header()
        self.create_main_content()
        self.create_footer()
        
        # Load initial data
        self.load_suggestions()
        
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
        """Create main content area with tabs"""
        # Create notebook-style tabs
        self.main_frame = ctk.CTkFrame(self.dialog)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Tab buttons
        tab_frame = ctk.CTkFrame(self.main_frame)
        tab_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.favorites_btn = ctk.CTkButton(
            tab_frame,
            text="⭐ Favorites",
            command=lambda: self.switch_tab("favorites"),
            width=120
        )
        self.favorites_btn.pack(side="left", padx=5)
        
        self.recent_btn = ctk.CTkButton(
            tab_frame,
            text="🕒 Recent",
            command=lambda: self.switch_tab("recent"),
            width=120
        )
        self.recent_btn.pack(side="left", padx=5)
        
        self.popular_btn = ctk.CTkButton(
            tab_frame,
            text="🔥 Popular",
            command=lambda: self.switch_tab("popular"),
            width=120
        )
        self.popular_btn.pack(side="left", padx=5)
        
        self.search_results_btn = ctk.CTkButton(
            tab_frame,
            text="🔍 Search Results",
            command=lambda: self.switch_tab("search"),
            width=140
        )
        self.search_results_btn.pack(side="left", padx=5)
        
        # Content area
        self.content_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Current tab
        self.current_tab = "favorites"
        self.switch_tab("favorites")
    
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
            "favorites": self.favorites_btn,
            "recent": self.recent_btn,
            "popular": self.popular_btn,
            "search": self.search_results_btn
        }
        
        for name, btn in buttons.items():
            if name == tab_name:
                btn.configure(fg_color=("blue", "darkblue"))
            else:
                btn.configure(fg_color=("gray70", "gray30"))
        
        # Load content for selected tab
        if tab_name == "favorites":
            self.load_favorites()
        elif tab_name == "recent":
            self.load_recent()
        elif tab_name == "popular":
            self.load_popular()
        elif tab_name == "search":
            self.display_search_results()
    
    def load_suggestions(self):
        """Load initial suggestions (favorites and recent)"""
        self.load_favorites()
    
    def load_favorites(self):
        """Load user's favorite locations"""
        self.clear_content()
        
        # Add loading indicator
        loading_label = ctk.CTkLabel(
            self.content_frame,
            text="Loading favorites...",
            font=ctk.CTkFont(size=14)
        )
        loading_label.pack(pady=20)
        
        # Load in background
        def load_data():
            favorites = self.location_manager.get_favorite_locations(self.employee_id)
            self.dialog.after(0, lambda: self.display_locations(favorites, "favorites"))
        
        threading.Thread(target=load_data, daemon=True).start()
    
    def load_recent(self):
        """Load recent locations"""
        self.clear_content()
        
        loading_label = ctk.CTkLabel(
            self.content_frame,
            text="Loading recent locations...",
            font=ctk.CTkFont(size=14)
        )
        loading_label.pack(pady=20)
        
        def load_data():
            recent = self.location_manager.get_recent_locations(self.employee_id)
            self.dialog.after(0, lambda: self.display_locations(recent, "recent"))
        
        threading.Thread(target=load_data, daemon=True).start()
    
    def load_popular(self):
        """Load popular locations"""
        self.clear_content()
        
        loading_label = ctk.CTkLabel(
            self.content_frame,
            text="Loading popular locations...",
            font=ctk.CTkFont(size=14)
        )
        loading_label.pack(pady=20)
        
        def load_data():
            popular = self.location_manager.get_popular_locations()
            self.dialog.after(0, lambda: self.display_locations(popular, "popular"))
        
        threading.Thread(target=load_data, daemon=True).start()
    
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
                "favorites": "No favorite locations yet.\nUse search to find and select locations.",
                "recent": "No recent locations.\nUse search to find new locations.",
                "popular": "No popular locations available.",
                "search": "No locations found.\nTry a different search term."
            }
            
            no_results_label = ctk.CTkLabel(
                self.content_frame,
                text=no_results_msg.get(tab_type, "No locations found."),
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_results_label.pack(pady=30)
            return
        
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
        
        # Additional info (for favorites/recent/popular)
        info_parts = []
        if location.get('is_favorite'):
            info_parts.append("⭐ Favorite")
        if location.get('is_recent'):
            info_parts.append("🕒 Recent")
        if location.get('is_popular'):
            info_parts.append("🔥 Popular")
        if location.get('use_count', 0) > 1:
            info_parts.append(f"Used {location['use_count']} times")
        
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
            self.callback(self.selected_location)
            self.dialog.destroy()
    
    def cancel_selection(self):
        """Cancel location selection"""
        self.callback(None)
        self.dialog.destroy()
