#!/usr/bin/env python3
"""
Test script for hybrid Haar+ArcFace face recognition accuracy
"""

import cv2
import time
import logging
from core.deepface_recognition import DeepFaceRecognitionSystem
from core.mongodb_manager import MongoDBManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_hybrid_recognition():
    """Test the hybrid recognition system accuracy"""
    
    print("🧪 Testing Hybrid Haar+ArcFace Recognition System")
    print("=" * 60)
    
    # Initialize MongoDB and face recognition
    try:
        db_manager = MongoDBManager()
        face_recognition = DeepFaceRecognitionSystem()
        
        # Load known faces from database
        employees = db_manager.get_all_employees()
        logger.info(f"Found {len(employees)} employees in database")
        
        known_faces = {}
        for emp in employees:
            if emp.get('face_vector'):
                known_faces[emp['employee_id']] = {
                    'embedding': emp['face_vector'],
                    'name': emp['name']
                }
        
        face_recognition.load_known_faces_from_dict(known_faces)
        logger.info(f"Loaded {len(known_faces)} face embeddings")
        
        # Test camera recognition
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return
        
        print("\n📹 Starting camera test...")
        print("Press 'q' to quit, 's' to test single frame")
        
        frame_count = 0
        recognition_count = 0
        total_confidence = 0.0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Test hybrid recognition every 10 frames
            if frame_count % 10 == 0:
                start_time = time.time()
                
                # Test hybrid extraction
                face_embedding, face_coords = face_recognition.extract_face_embedding_hybrid(frame)
                
                processing_time = time.time() - start_time
                
                if face_embedding is not None:
                    # Test recognition
                    employee_id, confidence = face_recognition.recognize_face(frame)
                    
                    if employee_id:
                        recognition_count += 1
                        total_confidence += confidence
                        
                        print(f"✅ Frame {frame_count}: {employee_id} (confidence: {confidence:.3f}, time: {processing_time:.3f}s)")
                    else:
                        print(f"❓ Frame {frame_count}: Unknown face (time: {processing_time:.3f}s)")
                else:
                    print(f"⚫ Frame {frame_count}: No face detected (time: {processing_time:.3f}s)")
                
                # Draw bounding box if face detected
                if face_coords:
                    x, y, w, h = face_coords
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    if face_embedding is not None:
                        employee_id, confidence = face_recognition.recognize_face(frame)
                        if employee_id:
                            label = f"{employee_id}: {confidence:.2f}"
                            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Display frame
            cv2.imshow('Hybrid Recognition Test', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Single frame test
                print(f"\n🔍 Single frame analysis (Frame {frame_count}):")
                
                # Test pure DeepFace
                start_time = time.time()
                pure_embedding, pure_coords = face_recognition.extract_face_embedding_deepface_only(frame)
                pure_time = time.time() - start_time
                
                # Test hybrid approach
                start_time = time.time()
                hybrid_embedding, hybrid_coords = face_recognition.extract_face_embedding_hybrid(frame)
                hybrid_time = time.time() - start_time
                
                print(f"  Pure DeepFace: {'✅' if pure_embedding is not None else '❌'} (time: {pure_time:.3f}s)")
                print(f"  Hybrid Approach: {'✅' if hybrid_embedding is not None else '❌'} (time: {hybrid_time:.3f}s)")
                
                if hybrid_embedding is not None:
                    employee_id, confidence = face_recognition.recognize_face(frame)
                    print(f"  Recognition: {employee_id or 'Unknown'} (confidence: {confidence:.3f})")
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Print statistics
        print(f"\n📊 Test Results:")
        print(f"  Total frames processed: {frame_count}")
        print(f"  Recognition attempts: {frame_count // 10}")
        print(f"  Successful recognitions: {recognition_count}")
        print(f"  Average confidence: {total_confidence / recognition_count if recognition_count > 0 else 0:.3f}")
        print(f"  Recognition rate: {recognition_count / (frame_count // 10) * 100 if frame_count > 0 else 0:.1f}%")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hybrid_recognition()
