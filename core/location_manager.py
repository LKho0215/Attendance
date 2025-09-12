"""
Location Manager for handling location selection when checking out
Uses OpenStreetMap Nominatim API for free geocoding services
"""

import requests
import json
import time
import sqlite3
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class LocationManager:
    def __init__(self, db_path="data/database/attendance.db"):
        self.db_path = db_path
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        self.user_agent = "AttendanceKiosk/1.0"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Rate limiting (Nominatim policy: max 1 request per second)
        self.last_request_time = 0
        self.min_request_interval = 1.1  # 1.1 seconds between requests
        
        # Initialize database
        self.init_location_database()
    
    def init_location_database(self):
        """Initialize location-related database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create location_history table for storing checkout locations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS location_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attendance_id INTEGER,
                    employee_id TEXT,
                    location_name TEXT,
                    location_address TEXT,
                    latitude REAL,
                    longitude REAL,
                    location_type TEXT,
                    timestamp DATETIME,
                    FOREIGN KEY (attendance_id) REFERENCES attendance (id)
                )
            ''')
            
            # Create favorite_locations table for frequently used locations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorite_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT,
                    location_name TEXT,
                    location_address TEXT,
                    latitude REAL,
                    longitude REAL,
                    use_count INTEGER DEFAULT 1,
                    last_used DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print("[LOCATION DEBUG] Location database tables initialized")
            
        except Exception as e:
            print(f"[LOCATION DEBUG] Database initialization error: {e}")
    
    def _rate_limit(self):
        """Enforce rate limiting for Nominatim API"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_locations(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for locations using Nominatim geocoding
        
        Args:
            query: Search query (e.g., "Starbucks", "123 Main St", "Hospital")
            limit: Maximum number of results to return
            
        Returns:
            List of location dictionaries with name, address, coordinates
        """
        if not query or len(query.strip()) < 2:
            return []
        
        try:
            self._rate_limit()
            
            params = {
                'q': query.strip(),
                'format': 'json',
                'limit': limit,
                'addressdetails': 1,
                'extratags': 1,
                'namedetails': 1
            }
            
            print(f"[LOCATION DEBUG] Searching for: '{query}'")
            response = self.session.get(f"{self.nominatim_url}/search", params=params, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            locations = []
            
            for result in results:
                location = {
                    'name': self._extract_location_name(result),
                    'address': result.get('display_name', ''),
                    'latitude': float(result.get('lat', 0)),
                    'longitude': float(result.get('lon', 0)),
                    'type': result.get('type', 'unknown'),
                    'category': result.get('class', 'place'),
                    'importance': result.get('importance', 0)
                }
                locations.append(location)
            
            print(f"[LOCATION DEBUG] Found {len(locations)} locations")
            return locations
            
        except requests.exceptions.RequestException as e:
            print(f"[LOCATION DEBUG] Network error during location search: {e}")
            return []
        except Exception as e:
            print(f"[LOCATION DEBUG] Error searching locations: {e}")
            return []
    
    def _extract_location_name(self, result: Dict) -> str:
        """Extract the best display name for a location"""
        # Priority order for location names
        name_fields = [
            'namedetails.name',
            'name',
            'display_name'
        ]
        
        # Try to get a good name
        if 'namedetails' in result and 'name' in result['namedetails']:
            return result['namedetails']['name']
        elif 'name' in result:
            return result['name']
        else:
            # Use the first part of display_name
            display_name = result.get('display_name', '')
            parts = display_name.split(',')
            return parts[0].strip() if parts else display_name
    
    def get_location_by_coordinates(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        Reverse geocoding - get location info from coordinates
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Location dictionary or None if not found
        """
        try:
            self._rate_limit()
            
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'addressdetails': 1,
                'extratags': 1,
                'namedetails': 1
            }
            
            response = self.session.get(f"{self.nominatim_url}/reverse", params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result and 'lat' in result:
                location = {
                    'name': self._extract_location_name(result),
                    'address': result.get('display_name', ''),
                    'latitude': float(result.get('lat', 0)),
                    'longitude': float(result.get('lon', 0)),
                    'type': result.get('type', 'unknown'),
                    'category': result.get('class', 'place')
                }
                return location
            
            return None
            
        except Exception as e:
            print(f"[LOCATION DEBUG] Error reverse geocoding: {e}")
            return None
    
    def save_checkout_location(self, attendance_id: int, employee_id: str, location: Dict) -> bool:
        """
        Save the selected checkout location to database
        
        Args:
            attendance_id: ID of the attendance record
            employee_id: Employee ID
            location: Location dictionary from search results
            
        Returns:
            True if saved successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO location_history 
                (attendance_id, employee_id, location_name, location_address, 
                 latitude, longitude, location_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                attendance_id,
                employee_id,
                location.get('name', ''),
                location.get('address', ''),
                location.get('latitude', 0),
                location.get('longitude', 0),
                location.get('type', 'unknown'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            conn.commit()
            conn.close()
            
            # Also update favorite locations
            self._update_favorite_location(employee_id, location)
            
            print(f"[LOCATION DEBUG] Saved checkout location for {employee_id}: {location.get('name')}")
            return True
            
        except Exception as e:
            print(f"[LOCATION DEBUG] Error saving checkout location: {e}")
            return False
    
    def _update_favorite_location(self, employee_id: str, location: Dict):
        """Update or create favorite location entry"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if this location already exists as favorite
            cursor.execute('''
                SELECT id, use_count FROM favorite_locations 
                WHERE employee_id = ? AND location_name = ? AND location_address = ?
            ''', (employee_id, location.get('name', ''), location.get('address', '')))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing favorite
                cursor.execute('''
                    UPDATE favorite_locations 
                    SET use_count = use_count + 1, last_used = ?
                    WHERE id = ?
                ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), existing[0]))
            else:
                # Create new favorite
                cursor.execute('''
                    INSERT INTO favorite_locations 
                    (employee_id, location_name, location_address, latitude, longitude, last_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    employee_id,
                    location.get('name', ''),
                    location.get('address', ''),
                    location.get('latitude', 0),
                    location.get('longitude', 0),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[LOCATION DEBUG] Error updating favorite location: {e}")
    
    def get_favorite_locations(self, employee_id: str, limit: int = 5) -> List[Dict]:
        """
        Get employee's favorite/frequently used locations
        
        Args:
            employee_id: Employee ID
            limit: Maximum number of favorites to return
            
        Returns:
            List of favorite location dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT location_name, location_address, latitude, longitude, use_count, last_used
                FROM favorite_locations 
                WHERE employee_id = ?
                ORDER BY use_count DESC, last_used DESC
                LIMIT ?
            ''', (employee_id, limit))
            
            favorites = []
            for row in cursor.fetchall():
                favorite = {
                    'name': row[0],
                    'address': row[1],
                    'latitude': row[2],
                    'longitude': row[3],
                    'use_count': row[4],
                    'last_used': row[5],
                    'is_favorite': True
                }
                favorites.append(favorite)
            
            conn.close()
            return favorites
            
        except Exception as e:
            print(f"[LOCATION DEBUG] Error getting favorites: {e}")
            return []
    
    def get_recent_locations(self, employee_id: str = None, limit: int = 10) -> List[Dict]:
        """
        Get recently used checkout locations (for all employees or specific employee)
        
        Args:
            employee_id: Employee ID (None for all employees)
            limit: Maximum number of recent locations
            
        Returns:
            List of recent location dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if employee_id:
                cursor.execute('''
                    SELECT DISTINCT location_name, location_address, latitude, longitude, 
                           COUNT(*) as use_count, MAX(timestamp) as last_used
                    FROM location_history 
                    WHERE employee_id = ?
                    GROUP BY location_name, location_address
                    ORDER BY last_used DESC
                    LIMIT ?
                ''', (employee_id, limit))
            else:
                cursor.execute('''
                    SELECT DISTINCT location_name, location_address, latitude, longitude,
                           COUNT(*) as use_count, MAX(timestamp) as last_used
                    FROM location_history 
                    GROUP BY location_name, location_address
                    ORDER BY last_used DESC
                    LIMIT ?
                ''', (limit,))
            
            recent = []
            for row in cursor.fetchall():
                location = {
                    'name': row[0],
                    'address': row[1],
                    'latitude': row[2],
                    'longitude': row[3],
                    'use_count': row[4],
                    'last_used': row[5],
                    'is_recent': True
                }
                recent.append(location)
            
            conn.close()
            return recent
            
        except Exception as e:
            print(f"[LOCATION DEBUG] Error getting recent locations: {e}")
            return []
    
    def get_popular_locations(self, limit: int = 10) -> List[Dict]:
        """Get most popular checkout locations across all employees"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT location_name, location_address, latitude, longitude,
                       COUNT(*) as use_count, MAX(timestamp) as last_used
                FROM location_history 
                GROUP BY location_name, location_address
                HAVING use_count > 1
                ORDER BY use_count DESC, last_used DESC
                LIMIT ?
            ''', (limit,))
            
            popular = []
            for row in cursor.fetchall():
                location = {
                    'name': row[0],
                    'address': row[1],
                    'latitude': row[2],
                    'longitude': row[3],
                    'use_count': row[4],
                    'last_used': row[5],
                    'is_popular': True
                }
                popular.append(location)
            
            conn.close()
            return popular
            
        except Exception as e:
            print(f"[LOCATION DEBUG] Error getting popular locations: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test connection to Nominatim API"""
        try:
            self._rate_limit()
            response = self.session.get(f"{self.nominatim_url}/status.php", timeout=5)
            return response.status_code == 200
        except:
            return False
