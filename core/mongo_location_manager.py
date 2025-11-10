from datetime import datetime
from core.mongodb_manager import MongoDBManager
import requests
import time

class MongoLocationManager:
    def __init__(self, db_manager=None):
        """Initialize with MongoDB manager"""
        if db_manager is None:
            self.db_manager = MongoDBManager()
        else:
            self.db_manager = db_manager
        
        # Rate limiting for API calls
        self.last_api_call = 0
        self.api_cooldown = 1.0  # seconds between API calls
        
        print("[MONGO LOCATION] Location manager initialized with MongoDB")
    
    def search_locations(self, query, limit=10):
        """Search for locations using OpenStreetMap Nominatim API"""
        try:
            # Rate limiting
            current_time = time.time()
            if current_time - self.last_api_call < self.api_cooldown:
                time.sleep(self.api_cooldown - (current_time - self.last_api_call))
            
            # Nominatim API endpoint
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': query,
                'format': 'json',
                'addressdetails': 1,
                'limit': limit,
                'countrycodes': 'my'  # Malaysia
            }
            
            headers = {
                'User-Agent': 'AttendanceSystem/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            self.last_api_call = time.time()
            
            if response.status_code == 200:
                locations = response.json()
                return [
                    {
                        'display_name': loc.get('display_name', ''),
                        'lat': float(loc.get('lat', 0)),
                        'lon': float(loc.get('lon', 0)),
                        'type': loc.get('type', ''),
                        'address': loc.get('address', {})
                    }
                    for loc in locations
                ]
            else:
                print(f"[MONGO LOCATION] API error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"[MONGO LOCATION ERROR] Search failed: {e}")
            return []