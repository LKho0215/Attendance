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
        
    def _rate_limit(self):
        """Enforce rate limiting for Nominatim API"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_locations(self, query: str, limit: int = 10) -> List[Dict]:
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
    
    def test_connection(self) -> bool:
        """Test connection to Nominatim API"""
        try:
            self._rate_limit()
            response = self.session.get(f"{self.nominatim_url}/status.php", timeout=5)
            return response.status_code == 200
        except:
            return False
