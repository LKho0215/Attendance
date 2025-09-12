import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import logging

class VectorizedFaceRecognitionSystem:
    """Face recognition system using HOG feature vectors stored in MongoDB"""
    
    def __init__(self, tolerance=0.6):
        self.tolerance = tolerance
        self.known_face_encodings = []  # List of face feature vectors
        self.known_face_names = []      # Corresponding names
        self.known_employee_ids = []    # Corresponding employee IDs
        
        # Initialize OpenCV components
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize HOG descriptor for feature extraction
        self.hog = cv2.HOGDescriptor()
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def extract_face_encoding(self, image_array):
        """Extract face feature vector from image array"""
        try:
            # Convert to grayscale if needed
            if len(image_array.shape) == 3:
                gray_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
            else:
                gray_image = image_array
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray_image, 1.3, 5)
            
            if len(faces) > 0:
                # Get the largest face
                face = max(faces, key=lambda rect: rect[2] * rect[3])
                x, y, w, h = face
                
                # Extract face ROI
                face_roi = gray_image[y:y+h, x:x+w]
                
                # Resize to standard size for consistent feature extraction
                face_roi = cv2.resize(face_roi, (128, 128))
                
                # Extract HOG features
                features = self.hog.compute(face_roi)
                
                if features is not None:
                    # Flatten and normalize the features
                    feature_vector = features.flatten()
                    # Normalize to unit length
                    norm = np.linalg.norm(feature_vector)
                    if norm > 0:
                        feature_vector = feature_vector / norm
                    
                    return feature_vector.tolist(), (x, y, w, h)
            
            return None, None
            
        except Exception as e:
            self.logger.error(f"Error extracting face encoding: {e}")
            return None, None
    
    def extract_face_encoding_from_file(self, image_path):
        """Extract face feature vector from image file"""
        try:
            # Load image file
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            
            if image is None:
                return None
                
            # Detect faces
            faces = self.face_cascade.detectMultiScale(image, 1.3, 5)
            
            if len(faces) > 0:
                # Get the largest face
                face = max(faces, key=lambda rect: rect[2] * rect[3])
                x, y, w, h = face
                
                # Extract face ROI
                face_roi = image[y:y+h, x:x+w]
                
                # Resize to standard size
                face_roi = cv2.resize(face_roi, (128, 128))
                
                # Extract HOG features
                features = self.hog.compute(face_roi)
                
                if features is not None:
                    # Flatten and normalize the features
                    feature_vector = features.flatten()
                    # Normalize to unit length
                    norm = np.linalg.norm(feature_vector)
                    if norm > 0:
                        feature_vector = feature_vector / norm
                    
                    return feature_vector.tolist()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting face encoding from file {image_path}: {e}")
            return None
    
    def load_known_faces(self, employees_data):
        """Load known faces from database (now using face vectors instead of image paths)"""
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_employee_ids = []
        
        for employee in employees_data:
            # Check if employee has face vector stored
            if employee.get('face_vector') and isinstance(employee['face_vector'], list):
                # Convert list back to numpy array for face_recognition library
                face_encoding = np.array(employee['face_vector'])
                
                # Validate encoding length (HOG descriptors can be much longer than 128)
                if len(face_encoding) > 100:  # Accept any reasonable length vector
                    self.known_face_encodings.append(face_encoding)
                    self.known_face_names.append(employee['name'])
                    self.known_employee_ids.append(employee['employee_id'])
                    
                    self.logger.info(f"Loaded face vector for {employee['name']} ({employee['employee_id']})")
                else:
                    self.logger.warning(f"Invalid face vector dimension for {employee['name']}: {len(face_encoding)}")
    
    def recognize_face(self, face_encoding_array):
        """Recognize a face from its feature vector"""
        if not self.known_face_encodings or face_encoding_array is None:
            return None, None, 1.0
        
        try:
            # Convert input to numpy array if it's a list
            if isinstance(face_encoding_array, list):
                face_encoding = np.array(face_encoding_array)
            else:
                face_encoding = face_encoding_array
            
            # Calculate cosine similarity with all known faces
            best_distance = float('inf')
            best_match_index = -1
            
            for i, known_encoding in enumerate(self.known_face_encodings):
                known_vector = np.array(known_encoding)
                
                # Calculate cosine distance (1 - cosine similarity)
                dot_product = np.dot(face_encoding, known_vector)
                norm_a = np.linalg.norm(face_encoding)
                norm_b = np.linalg.norm(known_vector)
                
                if norm_a > 0 and norm_b > 0:
                    cosine_similarity = dot_product / (norm_a * norm_b)
                    cosine_distance = 1.0 - cosine_similarity
                    
                    if cosine_distance < best_distance:
                        best_distance = cosine_distance
                        best_match_index = i
            
            # Check if the best match is within tolerance
            if best_match_index >= 0 and best_distance <= self.tolerance:
                employee_id = self.known_employee_ids[best_match_index]
                name = self.known_face_names[best_match_index]
                confidence = 1.0 - best_distance  # Convert distance to confidence score
                
                self.logger.info(f"Face recognized: {name} ({employee_id}) with confidence {confidence:.2f}")
                return employee_id, name, confidence
            else:
                self.logger.info(f"No match found. Best distance: {best_distance:.3f} (threshold: {self.tolerance})")
                return None, None, 0.0
                
        except Exception as e:
            self.logger.error(f"Error recognizing face: {e}")
            return None, None, 0.0
    
    def detect_and_recognize_faces_in_frame(self, frame):
        """Detect and recognize faces in a camera frame"""
        try:
            # Convert to grayscale for face detection
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray_frame, 1.3, 5)
            
            recognized_faces = []
            
            for (x, y, w, h) in faces:
                # Extract face ROI
                face_roi = gray_frame[y:y+h, x:x+w]
                face_roi = cv2.resize(face_roi, (128, 128))
                
                # Extract features
                features = self.hog.compute(face_roi)
                
                if features is not None:
                    # Flatten and normalize the features
                    feature_vector = features.flatten()
                    # Normalize to unit length
                    norm = np.linalg.norm(feature_vector)
                    if norm > 0:
                        feature_vector = feature_vector / norm
                    
                    # Recognize the face
                    employee_id, name, confidence = self.recognize_face(feature_vector)
                    
                    recognized_faces.append({
                        'location': (x, y, w, h),
                        'employee_id': employee_id,
                        'name': name,
                        'confidence': confidence,
                        'face_encoding': feature_vector.tolist()  # Store for potential saving
                    })
            
            return recognized_faces
            
        except Exception as e:
            self.logger.error(f"Error detecting/recognizing faces in frame: {e}")
            return []
    
    def draw_face_boxes(self, frame, recognized_faces):
        """Draw bounding boxes and labels on faces"""
        for face in recognized_faces:
            x, y, w, h = face['location']
            name = face['name']
            employee_id = face['employee_id']
            confidence = face.get('confidence', 0.0)
            
            # Choose color based on recognition status
            if name and confidence > 0.5:  # High confidence recognition
                color = (0, 255, 0)  # Green
                label = f"{name} ({employee_id}) - {confidence:.2f}"
            elif name:  # Low confidence recognition
                color = (0, 255, 255)  # Yellow
                label = f"{name}? ({employee_id}) - {confidence:.2f}"
            else:  # Unknown face
                color = (0, 0, 255)  # Red
                label = "Unknown"
            
            # Draw rectangle around face
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw label background
            cv2.rectangle(frame, (x, y - 40), (x + w, y), color, cv2.FILLED)
            
            # Draw label text
            cv2.putText(frame, label, (x + 6, y - 6), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
        
        return frame

class CameraManager:
    """Camera management class (unchanged from original)"""
    
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
