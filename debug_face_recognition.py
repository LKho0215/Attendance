#!/usr/bin/env python3
"""
Debug Face Recognition for Telegram Bot
Test face recognition capabilities with sample images
"""

import cv2
import numpy as np
import sys
import os
from PIL import Image
import tempfile

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

def test_face_recognition_debug():
    """Test face recognition with debug output"""
    print("🔍 Testing Face Recognition Debug Mode")
    print("=" * 50)
    
    try:
        from core.deepface_recognition import DeepFaceRecognitionSystem
        face_recognition = DeepFaceRecognitionSystem()
        print("✅ Face recognition system loaded")
        
        # Create a test image with more realistic face-like patterns
        test_image = create_test_face_image()
        print(f"📷 Created test image: {test_image.shape}")
        
        # Test 1: Fast face detection
        print("\n1️⃣ Testing fast face detection...")
        faces = face_recognition.detect_faces_fast(test_image)
        print(f"   Found {len(faces)} faces with fast detection")
        
        # Test 2: Hybrid embedding extraction
        print("\n2️⃣ Testing hybrid embedding extraction...")
        try:
            face_embedding, face_region = face_recognition.extract_face_embedding_hybrid(test_image)
            if face_embedding is not None:
                print(f"   ✅ Hybrid method success - embedding size: {len(face_embedding)}")
            else:
                print("   ❌ Hybrid method failed")
        except Exception as e:
            print(f"   ❌ Hybrid method error: {e}")
        
        # Test 3: DeepFace-only embedding extraction
        print("\n3️⃣ Testing DeepFace-only embedding extraction...")
        try:
            face_embedding, face_region = face_recognition.extract_face_embedding_deepface_only(test_image)
            if face_embedding is not None:
                print(f"   ✅ DeepFace-only method success - embedding size: {len(face_embedding)}")
            else:
                print("   ❌ DeepFace-only method failed")
        except Exception as e:
            print(f"   ❌ DeepFace-only method error: {e}")
        
        # Test 4: Recognition info
        print("\n4️⃣ Face detection system info:")
        try:
            info = face_recognition.get_face_detection_info()
            for key, value in info.items():
                print(f"   {key}: {value}")
        except Exception as e:
            print(f"   ❌ Info retrieval error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Face recognition test error: {e}")
        return False

def create_test_face_image():
    """Create a more realistic test image"""
    # Create a larger image with gradient patterns that might trigger face detection
    height, width = 400, 400
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add some realistic patterns
    # Face-like oval
    center_x, center_y = width // 2, height // 2
    
    # Create gradient background
    for y in range(height):
        for x in range(width):
            # Create a face-like gradient
            dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            if dist_from_center < 100:
                intensity = int(120 + 60 * np.cos(dist_from_center / 50))
                image[y, x] = [intensity, intensity, intensity]
            else:
                image[y, x] = [50, 50, 50]
    
    # Add some face-like features
    # Eyes
    cv2.circle(image, (center_x - 30, center_y - 20), 8, (30, 30, 30), -1)
    cv2.circle(image, (center_x + 30, center_y - 20), 8, (30, 30, 30), -1)
    
    # Nose
    cv2.circle(image, (center_x, center_y + 10), 5, (100, 100, 100), -1)
    
    # Mouth
    cv2.ellipse(image, (center_x, center_y + 40), (20, 8), 0, 0, 180, (30, 30, 30), 2)
    
    return image

def test_with_webcam():
    """Test face recognition with webcam"""
    print("\n📹 Testing with webcam...")
    
    try:
        from core.deepface_recognition import DeepFaceRecognitionSystem
        face_recognition = DeepFaceRecognitionSystem()
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open webcam")
            return False
        
        print("📷 Webcam opened. Press 'q' to quit, 'space' to test current frame")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to capture frame")
                break
            
            # Show frame
            cv2.putText(frame, "Press SPACE to test face recognition", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Webcam Face Test', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                # Test face recognition on current frame
                print("\n🔍 Testing current frame...")
                
                # Test fast detection
                faces = face_recognition.detect_faces_fast(frame)
                print(f"   Fast detection: {len(faces)} faces")
                
                # Test embedding extraction
                try:
                    face_embedding, face_region = face_recognition.extract_face_embedding_hybrid(frame)
                    if face_embedding is not None:
                        print(f"   ✅ Embedding extracted: size {len(face_embedding)}")
                    else:
                        print("   ❌ No embedding extracted")
                except Exception as e:
                    print(f"   ❌ Embedding error: {e}")
        
        cap.release()
        cv2.destroyAllWindows()
        return True
        
    except Exception as e:
        print(f"❌ Webcam test error: {e}")
        return False

def main():
    """Main debug function"""
    print("🐛 Face Recognition Debug Tool")
    print("=" * 40)
    
    choice = input("\nChoose test method:\n1. Test with synthetic image\n2. Test with webcam\n3. Both\nEnter choice (1-3): ").strip()
    
    if choice in ['1', '3']:
        test_face_recognition_debug()
    
    if choice in ['2', '3']:
        test_with_webcam()
    
    print("\n✅ Debug testing complete!")

if __name__ == "__main__":
    main()