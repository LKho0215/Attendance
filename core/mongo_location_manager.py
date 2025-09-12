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
        
        # Collections
        self.location_history = self.db_manager.db.location_history
        self.favorite_locations = self.db_manager.db.favorite_locations
        
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
    
    def save_checkout_location(self, attendance_id, employee_id, location_data):
        """Save checkout location to database"""
        try:
            location_doc = {
                "attendance_id": attendance_id,
                "employee_id": employee_id,
                "location_name": location_data.get('display_name', ''),
                "latitude": location_data.get('lat', 0),
                "longitude": location_data.get('lon', 0),
                "address": location_data.get('address', {}),
                "timestamp": datetime.now()
            }
            
            result = self.location_history.insert_one(location_doc)
            print(f"[MONGO LOCATION] Saved checkout location for {employee_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"[MONGO LOCATION ERROR] Failed to save location: {e}")
            return None
    
    def add_favorite_location(self, employee_id, location_data, custom_name=None):
        """Add a location to employee's favorites"""
        try:
            favorite_doc = {
                "employee_id": employee_id,
                "custom_name": custom_name or location_data.get('display_name', ''),
                "location_name": location_data.get('display_name', ''),
                "latitude": location_data.get('lat', 0),
                "longitude": location_data.get('lon', 0),
                "address": location_data.get('address', {}),
                "created_at": datetime.now()
            }
            
            result = self.favorite_locations.insert_one(favorite_doc)
            print(f"[MONGO LOCATION] Added favorite location for {employee_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"[MONGO LOCATION ERROR] Failed to add favorite: {e}")
            return None
    
    def get_favorite_locations(self, employee_id, limit=10):
        """Get employee's favorite locations"""
        try:
            favorites = self.favorite_locations.find(
                {"employee_id": employee_id}
            ).sort("created_at", -1).limit(limit)
            
            return [
                {
                    'display_name': fav['custom_name'],
                    'lat': fav['latitude'],
                    'lon': fav['longitude'],
                    'type': 'favorite',
                    'address': fav.get('address', {})
                }
                for fav in favorites
            ]
            
        except Exception as e:
            print(f"[MONGO LOCATION ERROR] Failed to get favorites: {e}")
            return []
    
    def get_recent_locations(self, employee_id, limit=5):
        """Get employee's recent checkout locations"""
        try:
            recent = self.location_history.find(
                {"employee_id": employee_id}
            ).sort("timestamp", -1).limit(limit)
            
            return [
                {
                    'display_name': loc['location_name'],
                    'lat': loc['latitude'],
                    'lon': loc['longitude'],
                    'type': 'recent',
                    'address': loc.get('address', {})
                }
                for loc in recent
            ]
            
        except Exception as e:
            print(f"[MONGO LOCATION ERROR] Failed to get recent locations: {e}")
            return []
    
    def get_popular_locations(self, limit=10):
        """Get most popular checkout locations across all employees"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "location_name": "$location_name",
                            "latitude": "$latitude",
                            "longitude": "$longitude"
                        },
                        "count": {"$sum": 1},
                        "address": {"$first": "$address"}
                    }
                },
                {
                    "$sort": {"count": -1}
                },
                {
                    "$limit": limit
                },
                {
                    "$project": {
                        "display_name": "$_id.location_name",
                        "lat": "$_id.latitude",
                        "lon": "$_id.longitude",
                        "type": "popular",
                        "address": "$address",
                        "usage_count": "$count"
                    }
                }
            ]
            
            return list(self.location_history.aggregate(pipeline))
            
        except Exception as e:
            print(f"[MONGO LOCATION ERROR] Failed to get popular locations: {e}")
            return []
    
    def remove_favorite_location(self, employee_id, location_name):
        """Remove a location from employee's favorites"""
        try:
            result = self.favorite_locations.delete_one({
                "employee_id": employee_id,
                "custom_name": location_name
            })
            
            if result.deleted_count > 0:
                print(f"[MONGO LOCATION] Removed favorite location for {employee_id}")
                return True
            return False
            
        except Exception as e:
            print(f"[MONGO LOCATION ERROR] Failed to remove favorite: {e}")
            return False
