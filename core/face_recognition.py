import cv2
import numpy as np
import os
from typing import List, Tuple, Optional

class FaceRecognitionSystem:
    def __init__(self, tolerance=0.6):
        self.tolerance = tolerance
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_employee_ids = []
        
        # Initialize OpenCV face detector
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize face recognizer
        self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.is_trained = False
    
    def load_known_faces(self, employees_data):
        """Load known faces from database"""
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_employee_ids = []
        
        faces = []
        labels = []
        
        for i, employee in enumerate(employees_data):
            if employee.get('face_image_path') and os.path.exists(employee['face_image_path']):
                # Load and process face image
                img = cv2.imread(employee['face_image_path'], cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    # Resize to standard size
                    img = cv2.resize(img, (200, 200))
                    faces.append(img)
                    labels.append(i)
                    self.known_face_names.append(employee['name'])
                    self.known_employee_ids.append(employee['employee_id'])
        
        # Train the recognizer if we have faces
        if faces:
            self.face_recognizer.train(faces, np.array(labels))
            self.is_trained = True
    
    def encode_face_from_image(self, image_path):
        """Extract face encoding from an image file"""
        try:
            # Load image in grayscale
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                return None
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(image, 1.3, 5)
            
            if len(faces) > 0:
                # Get the first face
                (x, y, w, h) = faces[0]
                face_roi = image[y:y+h, x:x+w]
                # Resize to standard size
                face_roi = cv2.resize(face_roi, (200, 200))
                return face_roi
            else:
                return None
        except Exception as e:
            print(f"Error encoding face from {image_path}: {e}")
            return None
    
    def encode_face_from_array(self, image_array):
        """Extract face encoding from a numpy array (camera frame)"""
        try:
            # Convert to grayscale if needed
            if len(image_array.shape) == 3:
                gray_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
            else:
                gray_image = image_array
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray_image, 1.3, 5)
            
            if len(faces) > 0:
                # Get the first face
                (x, y, w, h) = faces[0]
                face_roi = gray_image[y:y+h, x:x+w]
                # Resize to standard size
                face_roi = cv2.resize(face_roi, (200, 200))
                return face_roi
            else:
                return None
        except Exception as e:
            print(f"Error encoding face from camera: {e}")
            return None
    
    def recognize_face(self, face_image):
        """Recognize a face from its image"""
        if not self.is_trained:
            return None, None
        
        try:
            # Predict using the trained recognizer
            label, confidence = self.face_recognizer.predict(face_image)
            
            # Lower confidence means better match (distance-based)
            if confidence < 100:  # Threshold for recognition
                if label < len(self.known_employee_ids):
                    return (
                        self.known_employee_ids[label],
                        self.known_face_names[label]
                    )
        except Exception as e:
            print(f"Error recognizing face: {e}")
        
        return None, None
    
    def detect_faces_in_frame(self, frame):
        """Detect faces in a camera frame and return their locations"""
        # Convert to grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray_frame, 1.3, 5)
        
        return faces, gray_frame
    
    def process_video_frame(self, frame):
        """Process a video frame and return recognized faces with their locations"""
        faces, gray_frame = self.detect_faces_in_frame(frame)
        
        recognized_faces = []
        
        for (x, y, w, h) in faces:
            # Extract face ROI
            face_roi = gray_frame[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (200, 200))
            
            # Recognize face
            employee_id, name = self.recognize_face(face_roi)
            
            recognized_faces.append({
                'location': (x, y, w, h),
                'employee_id': employee_id,
                'name': name,
                'face_roi': face_roi
            })
        
        return recognized_faces
    
    def draw_face_boxes(self, frame, recognized_faces):
        """Draw bounding boxes and labels on faces"""
        for face in recognized_faces:
            x, y, w, h = face['location']
            name = face['name']
            employee_id = face['employee_id']
            
            # Choose color based on recognition status
            color = (0, 255, 0) if name else (0, 0, 255)  # Green if recognized, Red if not
            
            # Draw rectangle around face
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label = f"{name} ({employee_id})" if name else "Unknown"
            cv2.rectangle(frame, (x, y - 40), (x + w, y), color, cv2.FILLED)
            cv2.putText(frame, label, (x + 6, y - 6), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
        
        return frame
    
    def save_face_image(self, frame, face_location, employee_id, save_dir="data/faces"):
        """Save a cropped face image for an employee"""
        try:
            os.makedirs(save_dir, exist_ok=True)
            
            x, y, w, h = face_location
            face_image = frame[y:y+h, x:x+w]
            
            # Resize face image to standard size
            face_image = cv2.resize(face_image, (200, 200))
            
            # Save image
            image_path = os.path.join(save_dir, f"{employee_id}.jpg")
            cv2.imwrite(image_path, face_image)
            
            return image_path
        except Exception as e:
            print(f"Error saving face image: {e}")
            return None

class CameraManager:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.is_active = False
    
    def start_camera(self):
        """Start the camera with optimized settings"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                # Set camera properties for better performance
                self.cap.set(cv2.CAP_PROP_FPS, 30)  # Set to 30 FPS
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Standard width
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Standard height
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize delay
                
                # Print actual settings achieved
                actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"[CAMERA DEBUG] Camera settings - FPS: {actual_fps}, Resolution: {actual_width}x{actual_height}")
                
                self.is_active = True
                return True
            return False
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop the camera"""
        if self.cap:
            self.cap.release()
            self.is_active = False
    
    def get_frame(self):
        """Get a frame from the camera"""
        if self.cap and self.is_active:
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None
    
    def is_camera_active(self):
        """Check if camera is active"""
        return self.is_active
