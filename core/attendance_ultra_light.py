"""
Integration module for Ultra Lightweight Face Detection with the Attendance System
Provides high-performance face detection for attendance tracking
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import time
from datetime import datetime
import hashlib
import os
from pathlib import Path

# Import ultra light face detector
try:
    from .ultra_light_face_detector import UltraLightFaceDetector
except ImportError:
    # For standalone testing
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from ultra_light_face_detector import UltraLightFaceDetector


class AttendanceUltraLightDetector:
    """
    Ultra Lightweight Face Detection system integrated with attendance tracking
    Optimized for speed and accuracy in attendance scenarios
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.7,
                 min_face_size: int = 40,
                 max_faces_per_frame: int = 5):
        """
        Initialize the attendance face detector
        
        Args:
            confidence_threshold: Minimum confidence for face detection
            min_face_size: Minimum face size in pixels (width or height)
            max_faces_per_frame: Maximum number of faces to process per frame
        """
        self.confidence_threshold = confidence_threshold
        self.min_face_size = min_face_size
        self.max_faces_per_frame = max_faces_per_frame
        
        # Initialize the detector
        print("[ATTENDANCE DETECTOR] Initializing Ultra Light Face Detector...")
        self.detector = UltraLightFaceDetector(confidence_threshold=confidence_threshold)
        
        # Performance tracking
        self.total_detections = 0
        self.total_frames = 0
        self.last_detection_time = time.time()
        
        # Face tracking for attendance
        self.face_tracking = {}
        self.face_id_counter = 0
        
        print("[ATTENDANCE DETECTOR] Ultra Light Face Detector ready!")
    
    def detect_faces_for_attendance(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces optimized for attendance system
        
        Args:
            frame: Input video frame
            
        Returns:
            List of face detection dictionaries with attendance-specific data
        """
        self.total_frames += 1
        
        # Detect faces using ultra light detector
        raw_detections = self.detector.detect_faces(frame)
        
        # Filter and process detections for attendance
        attendance_faces = []
        
        for i, (x1, y1, x2, y2, confidence) in enumerate(raw_detections):
            if i >= self.max_faces_per_frame:
                break
            
            # Calculate face size
            face_width = x2 - x1
            face_height = y2 - y1
            face_size = min(face_width, face_height)
            
            # Filter by minimum face size
            if face_size < self.min_face_size:
                continue
            
            # Extract face region
            face_region = frame[y1:y2, x1:x2]
            
            # Create face data for attendance
            face_data = {
                'id': self._generate_face_id(),
                'bbox': (x1, y1, x2, y2),
                'confidence': confidence,
                'face_size': face_size,
                'face_region': face_region,
                'center': ((x1 + x2) // 2, (y1 + y2) // 2),
                'area': face_width * face_height,
                'aspect_ratio': face_width / face_height if face_height > 0 else 1.0,
                'timestamp': datetime.now(),
                'frame_number': self.total_frames
            }
            
            attendance_faces.append(face_data)
            self.total_detections += 1
        
        if attendance_faces:
            self.last_detection_time = time.time()
        
        return attendance_faces
    
    def get_best_face(self, faces: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Select the best face for attendance from multiple detections
        
        Args:
            faces: List of face detection dictionaries
            
        Returns:
            Best face dictionary or None
        """
        if not faces:
            return None
        
        if len(faces) == 1:
            return faces[0]
        
        # Score faces based on multiple criteria
        scored_faces = []
        
        for face in faces:
            score = 0
            
            # Confidence score (weight: 40%)
            score += face['confidence'] * 0.4
            
            # Size score - prefer larger faces (weight: 30%)
            size_score = min(face['face_size'] / 200.0, 1.0)  # Normalize to 200px
            score += size_score * 0.3
            
            # Position score - prefer center faces (weight: 20%)
            center_x, center_y = face['center']
            # Assuming frame is roughly 640x480, prefer faces near center
            center_score = 1.0 - (abs(center_x - 320) / 320.0 + abs(center_y - 240) / 240.0) / 2.0
            score += max(center_score, 0) * 0.2
            
            # Aspect ratio score - prefer more square faces (weight: 10%)
            aspect_ratio = face['aspect_ratio']
            aspect_score = 1.0 - abs(aspect_ratio - 1.0)  # Perfect square is 1.0
            score += max(aspect_score, 0) * 0.1
            
            scored_faces.append((score, face))
        
        # Return the best scored face
        scored_faces.sort(key=lambda x: x[0], reverse=True)
        return scored_faces[0][1]
    
    def _generate_face_id(self) -> str:
        """Generate a unique face ID for tracking"""
        self.face_id_counter += 1
        timestamp = int(time.time() * 1000)  # milliseconds
        return f"face_{timestamp}_{self.face_id_counter}"
    
    def save_face_for_attendance(self, face_data: Dict[str, Any], employee_id: str, 
                               save_dir: str = "data/faces") -> Optional[str]:
        """
        Save a detected face for attendance/registration purposes
        
        Args:
            face_data: Face detection dictionary
            employee_id: Employee ID for naming
            save_dir: Directory to save face images
            
        Returns:
            Path to saved image or None if failed
        """
        try:
            # Create save directory
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            face_hash = hashlib.md5(face_data['face_region'].tobytes()).hexdigest()[:8]
            filename = f"{employee_id}_{timestamp}_{face_hash}.jpg"
            full_path = save_path / filename
            
            # Save face image
            success = cv2.imwrite(str(full_path), face_data['face_region'])
            
            if success:
                print(f"[ATTENDANCE DETECTOR] Saved face: {full_path}")
                return str(full_path)
            else:
                print(f"[ATTENDANCE DETECTOR ERROR] Failed to save face: {full_path}")
                return None
                
        except Exception as e:
            print(f"[ATTENDANCE DETECTOR ERROR] Error saving face: {e}")
            return None
    
    def draw_attendance_overlay(self, frame: np.ndarray, faces: List[Dict[str, Any]], 
                              best_face: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """
        Draw attendance-specific overlay on frame
        
        Args:
            frame: Input frame
            faces: List of detected faces
            best_face: The selected best face (if any)
            
        Returns:
            Frame with overlay
        """
        result_frame = frame.copy()
        
        # Draw all detected faces
        for face in faces:
            x1, y1, x2, y2 = face['bbox']
            confidence = face['confidence']
            
            # Color based on whether this is the best face
            is_best = best_face and face['id'] == best_face['id']
            color = (0, 255, 0) if is_best else (0, 255, 255)  # Green for best, yellow for others
            thickness = 3 if is_best else 2
            
            # Draw bounding box
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw confidence and face info
            label = f"Face: {confidence:.2f}"
            if is_best:
                label += " [BEST]"
            
            # Background for text
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
            cv2.rectangle(result_frame, 
                         (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), 
                         color, -1)
            
            # Text
            cv2.putText(result_frame, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Draw face center
            center = face['center']
            cv2.circle(result_frame, center, 3, color, -1)
        
        # Draw performance stats
        fps = self.detector.get_fps()
        stats = [
            f"FPS: {fps:.1f}",
            f"Faces: {len(faces)}",
            f"Total Detections: {self.total_detections}",
            f"Frames: {self.total_frames}"
        ]
        
        y_offset = 30
        for stat in stats:
            cv2.putText(result_frame, stat, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_offset += 25
        
        return result_frame
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics"""
        fps = self.detector.get_fps()
        detection_rate = (self.total_detections / self.total_frames * 100) if self.total_frames > 0 else 0
        
        return {
            'fps': fps,
            'total_frames': self.total_frames,
            'total_detections': self.total_detections,
            'detection_rate': detection_rate,
            'avg_detections_per_frame': self.total_detections / self.total_frames if self.total_frames > 0 else 0,
            'last_detection_time': self.last_detection_time
        }
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.total_detections = 0
        self.total_frames = 0
        self.last_detection_time = time.time()
        print("[ATTENDANCE DETECTOR] Statistics reset")


# Convenience functions for easy integration
def create_attendance_detector(confidence_threshold: float = 0.7) -> AttendanceUltraLightDetector:
    """Create an attendance-optimized face detector"""
    return AttendanceUltraLightDetector(confidence_threshold=confidence_threshold)


def quick_face_detection_test():
    """Quick test function for the attendance detector"""
    print("Testing Attendance Ultra Light Detector...")
    
    detector = create_attendance_detector(confidence_threshold=0.5)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return
    
    try:
        for i in range(100):  # Test for 100 frames
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect faces
            faces = detector.detect_faces_for_attendance(frame)
            best_face = detector.get_best_face(faces)
            
            # Draw overlay
            result_frame = detector.draw_attendance_overlay(frame, faces, best_face)
            
            # Display
            cv2.imshow("Attendance Face Detection Test", result_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    # Print stats
    stats = detector.get_performance_stats()
    print(f"\n📊 Test Results:")
    for key, value in stats.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    quick_face_detection_test()