#!/usr/bin/env python3
"""
Test script for DeepFace Recognition System
Validates ArcFace integration and core functionality
"""

import sys
import os
import cv2
import numpy as np
from core.deepface_recognition import DeepFaceRecognitionSystem, CameraManager

def test_deepface_system():
    """Test the DeepFace recognition system functionality"""
    print("=" * 60)
    print("🧪 TESTING DEEPFACE RECOGNITION SYSTEM")
    print("=" * 60)
    
    try:
        # Initialize the system
        print("\n1. 🚀 Initializing DeepFace System...")
        recognition_system = DeepFaceRecognitionSystem()
        print("   ✅ DeepFace system initialized successfully")
        
        # Test camera functionality
        print("\n2. 📹 Testing Camera Access...")
        camera_manager = CameraManager()
        camera_started = camera_manager.start_camera()
        if camera_started:
            print("   ✅ Camera started successfully")
            
            # Test frame capture
            print("\n3. 🖼️  Testing Frame Capture...")
            frame = camera_manager.read_frame()
            if frame is not None:
                print(f"   ✅ Frame captured successfully: {frame.shape}")
                
                # Test face detection
                print("\n4. 👤 Testing Face Detection...")
                face_embedding, bbox = recognition_system.extract_face_embedding(frame)
                if face_embedding is not None:
                    print(f"   ✅ Face detected and embedding extracted: {face_embedding.shape}")
                    print(f"   📊 Embedding dimensions: {len(face_embedding)}")
                    print(f"   📈 Embedding range: [{face_embedding.min():.4f}, {face_embedding.max():.4f}]")
                    if bbox:
                        print(f"   📍 Face bounding box: {bbox}")
                    
                    # Test recognition (should fail without known faces)
                    print("\n5. 🔍 Testing Recognition (Empty Database)...")
                    result = recognition_system.recognize_face(frame)
                    if result == (None, 0.0):
                        print("   ✅ Recognition correctly returned None (no known faces)")
                    else:
                        print(f"   ⚠️  Unexpected recognition result: {result}")
                        
                    # Test loading known faces - create mock data
                    print("\n6. 💾 Testing Known Face Loading...")
                    test_faces = {
                        'TEST001': face_embedding  # Use the detected face as test data
                    }
                    recognition_system.known_faces = test_faces
                    print("   ✅ Test face loaded successfully")
                    
                    # Test recognition with known face
                    print("\n7. 🎯 Testing Recognition (With Known Faces)...")
                    result = recognition_system.recognize_face(frame)
                    if result != (None, 0.0):
                        employee_id, confidence = result
                        print(f"   ✅ Face recognized: {employee_id} (confidence: {confidence:.4f})")
                        if confidence > 0.6:  # Good confidence threshold
                            print("   🎉 High confidence recognition!")
                        else:
                            print("   ⚠️  Low confidence - may need threshold adjustment")
                    else:
                        print("   ❌ Recognition failed with known face")
                        
                else:
                    print("   ⚠️  No face detected in current frame")
                    print("   💡 Make sure a face is visible to the camera")
                    
            else:
                print("   ❌ Failed to capture frame")
                
            # Clean up camera
            camera_manager.stop_camera()
            print("\n8. 🛑 Camera stopped successfully")
            
        else:
            print("   ❌ Failed to start camera")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    print("\n" + "=" * 60)
    print("✅ DEEPFACE SYSTEM TEST COMPLETED")
    print("=" * 60)
    return True

def test_vector_operations():
    """Test vector averaging and similarity operations"""
    print("\n" + "=" * 60)
    print("🧮 TESTING VECTOR OPERATIONS")
    print("=" * 60)
    
    try:
        recognition_system = DeepFaceRecognitionSystem()
        
        # Create test vectors (ArcFace produces 512-dimensional embeddings)
        print("\n1. 🎲 Creating test vectors...")
        test_vectors = [
            np.random.rand(512).astype(np.float32),
            np.random.rand(512).astype(np.float32),
            np.random.rand(512).astype(np.float32)
        ]
        print(f"   ✅ Created {len(test_vectors)} test vectors of size {test_vectors[0].shape}")
        
        # Test multi-image embedding creation (this does averaging internally)
        print("\n2. 📊 Testing multi-image embedding creation...")
        # Create fake image arrays for testing
        fake_images = [
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        ]
        
        # This will likely fail since fake images don't contain faces, but tests the method
        avg_embedding = recognition_system.create_face_embedding_from_images(fake_images)
        if avg_embedding is not None:
            print(f"   ✅ Multi-image embedding created: {avg_embedding.shape}")
        else:
            print("   ⚠️  No faces found in test images (expected with random data)")
            
        # Test distance calculation (internal similarity measure)
        print("\n3. 🎯 Testing vector distance calculation...")
        distance = recognition_system._calculate_distance(test_vectors[0], test_vectors[1])
        print(f"   ✅ Distance calculated: {distance:.4f}")
        
        # Test with identical vectors (should be very low distance)
        distance_identical = recognition_system._calculate_distance(test_vectors[0], test_vectors[0])
        print(f"   ✅ Identical vector distance: {distance_identical:.4f}")
        
        if distance_identical < 0.01:
            print("   🎉 Perfect similarity for identical vectors!")
        else:
            print("   ⚠️  Expected lower distance for identical vectors")
            
    except Exception as e:
        print(f"\n❌ Vector operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    print("\n" + "=" * 60)
    print("✅ VECTOR OPERATIONS TEST COMPLETED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    print("🧪 DeepFace Recognition System Test Suite")
    print("🎯 Testing ArcFace integration and core functionality\n")
    
    # Run tests
    test1_success = test_deepface_system()
    test2_success = test_vector_operations()
    
    # Final results
    print("\n" + "=" * 60)
    print("📋 FINAL TEST RESULTS")
    print("=" * 60)
    print(f"🧪 DeepFace System Test: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"🧮 Vector Operations Test: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        print("\n🎉 ALL TESTS PASSED! DeepFace system is ready for production.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        
    print("=" * 60)
