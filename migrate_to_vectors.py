#!/usr/bin/env python3
"""
Migration script to convert existing face image paths to face embedding vectors.
This script will:
1. Load employees with face_image_path
2. Extract face vectors from the image files
3. Store the vectors in MongoDB
4. Optionally keep or remove the old image files
"""

import sys
import os
sys.path.append('.')

from core.mongodb_manager import MongoDBManager
from core.face_recognition_vector import VectorizedFaceRecognitionSystem
import numpy as np

def migrate_face_images_to_vectors():
    """Migrate existing face images to embedding vectors"""
    
    print("🔄 Starting face image to vector migration...")
    
    # Initialize components
    db = MongoDBManager()
    face_system = VectorizedFaceRecognitionSystem()
    
    # Get all employees with face images
    employees_with_images = db.get_all_face_images()
    
    if not employees_with_images:
        print("ℹ️  No employees with face images found. Migration complete.")
        return
    
    print(f"📋 Found {len(employees_with_images)} employees with face images")
    
    successful_migrations = 0
    failed_migrations = 0
    
    for employee in employees_with_images:
        employee_id = employee['employee_id']
        name = employee['name']
        image_path = employee['face_image_path']
        
        print(f"\n👤 Processing {name} ({employee_id})")
        print(f"   Image path: {image_path}")
        
        # Check if image path exists and is valid
        if not image_path or not os.path.exists(image_path):
            print(f"   ❌ Image file not found: {image_path}")
            failed_migrations += 1
            continue
        
        # Extract face vector from image
        try:
            face_vector = face_system.extract_face_encoding_from_file(image_path)
            
            if face_vector is None:
                print(f"   ❌ Could not extract face from image")
                failed_migrations += 1
                continue
            
            print(f"   ✅ Extracted face vector ({len(face_vector)} dimensions)")
            
            # Store face vector in database
            success = db.update_employee_face_vector(employee_id, face_vector)
            
            if success:
                print(f"   ✅ Stored face vector in database")
                successful_migrations += 1
            else:
                print(f"   ❌ Failed to store face vector in database")
                failed_migrations += 1
                
        except Exception as e:
            print(f"   ❌ Error processing {name}: {e}")
            failed_migrations += 1
    
    # Summary
    print(f"\n📊 Migration Summary:")
    print(f"   ✅ Successful: {successful_migrations}")
    print(f"   ❌ Failed: {failed_migrations}")
    print(f"   📈 Total processed: {successful_migrations + failed_migrations}")
    
    if successful_migrations > 0:
        print(f"\n🎉 Migration completed! {successful_migrations} employees now have face vectors.")
        
        # Ask if user wants to keep or remove image files
        while True:
            choice = input("\n🗂️  Keep original image files? (y/n): ").lower().strip()
            if choice in ['y', 'yes']:
                print("📁 Original image files will be kept.")
                break
            elif choice in ['n', 'no']:
                print("🗑️  Original image files will be removed...")
                remove_migrated_images(employees_with_images, successful_migrations)
                break
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    else:
        print("\n⚠️  No successful migrations. Please check your image files and try again.")

def remove_migrated_images(employees_with_images, successful_count):
    """Remove original image files after successful migration"""
    
    # Re-verify which employees now have face vectors
    db = MongoDBManager()
    removed_count = 0
    
    for employee in employees_with_images:
        employee_id = employee['employee_id']
        image_path = employee['face_image_path']
        
        # Check if employee now has face vector
        if db.has_face_vector(employee_id):
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"   🗑️  Removed: {image_path}")
                    removed_count += 1
                    
                    # Clear the face_image_path in database
                    db.employees.update_one(
                        {"employee_id": employee_id},
                        {"$unset": {"face_image_path": ""}}
                    )
                    
            except Exception as e:
                print(f"   ❌ Failed to remove {image_path}: {e}")
    
    print(f"🗑️  Removed {removed_count} image files.")

def test_vectorized_system():
    """Test the new vectorized face recognition system"""
    
    print("\n🧪 Testing vectorized face recognition system...")
    
    db = MongoDBManager()
    face_system = VectorizedFaceRecognitionSystem()
    
    # Load face vectors
    employees_with_vectors = db.get_all_face_vectors()
    
    if not employees_with_vectors:
        print("❌ No employees with face vectors found. Run migration first.")
        return
    
    print(f"✅ Loaded {len(employees_with_vectors)} employee face vectors")
    
    # Load into face recognition system
    face_system.load_known_faces(employees_with_vectors)
    
    print(f"✅ Face recognition system loaded with {len(face_system.known_face_encodings)} faces")
    print(f"   Employees: {', '.join(face_system.known_face_names)}")

if __name__ == "__main__":
    print("🚀 Face Recognition Vector Migration Tool")
    print("=" * 50)
    
    while True:
        print("\nChoose an option:")
        print("1. Migrate face images to vectors")
        print("2. Test vectorized system")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            migrate_face_images_to_vectors()
        elif choice == '2':
            test_vectorized_system()
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
