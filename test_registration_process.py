#!/usr/bin/env python3
"""
Simple test script to test the registration function without the full GUI
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from core.mongodb_manager import MongoDBManager
from core.face_recognition_vector import VectorizedFaceRecognitionSystem
import numpy as np

def test_registration_process():
    """Test just the registration process"""
    
    print("🧪 Testing Employee Registration Process...")
    
    try:
        # Initialize components
        db = MongoDBManager()
        face_recognition = VectorizedFaceRecognitionSystem()
        
        print("✅ Database and Face Recognition initialized")
        
        # Test employee data
        test_employee_id = "00999"
        test_employee_name = "Test Registration User"
        test_department = "IT Department"
        
        # Check if employee already exists (and remove if testing)
        existing = db.get_employee(test_employee_id)
        if existing:
            print(f"⚠️ Test employee {test_employee_id} already exists - this is expected for testing")
        
        # Create a dummy face vector for testing (since we can't capture real faces in script)
        dummy_vector = np.random.rand(3780).tolist()  # HOG vector size
        
        # Test adding employee with face vector
        success = db.add_employee_with_face_vector(
            employee_id=test_employee_id,
            name=test_employee_name,
            face_vector=dummy_vector,
            department=test_department
        )
        
        if success:
            print(f"✅ Employee registration test successful!")
            print(f"   • Employee ID: {test_employee_id}")
            print(f"   • Name: {test_employee_name}")
            print(f"   • Department: {test_department}")
            print(f"   • Face vector: {len(dummy_vector)} dimensions")
        else:
            print("❌ Employee registration test failed")
        
        # Clean up test data
        if success:
            # You might want to remove the test employee here if needed
            print("💡 Test employee created - you can remove manually if needed")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_registration_process()
