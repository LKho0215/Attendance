#!/usr/bin/env python3
"""
DeepFace-based Face Recognition System using ArcFace model
Provides state-of-the-art face recognition accuracy for the attendance system
"""

import os
import numpy as np
import cv2
import logging
import threading
import time
import gc  # For garbage collection monitoring
from queue import Queue, Empty
from typing import Optional, Tuple, List
import tempfile
from deepface import DeepFace
from PIL import Image
import base64
from PIL import Image
import io
import psutil  # For CPU monitoring

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepFaceRecognitionSystem:
    """
    Hybrid face recognition system:
    - Uses OpenCV Haar Cascades for fast face detection and cropping
    - Uses DeepFace ArcFace for high-accuracy feature extraction and recognition
    """
    
    def __init__(self, model_name='Facenet', detector_backend='opencv'):
        """
        Initialize the hybrid face recognition system
        
        Args:
            model_name: Face recognition model ('Facenet', 'ArcFace', 'VGG-Face', etc.)
                       Using Facenet (MobileFaceNet) for lightweight performance
            detector_backend: Face detection backend (not used, we use Haar)
        """
        self.model_name = model_name
        self.detector_backend = detector_backend
        self.known_faces = {}  # employee_id -> face_embedding
        
        # Initialize Haar Cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        logger.info("✅ Haar Cascade face detector loaded")
        
        # DeepFace model settings - optimized for MobileFaceNet
        self.target_size = (160, 160)  # MobileFaceNet input size (smaller than ArcFace)
        self.threshold = 0.75  # Adjusted threshold for MobileFaceNet (slightly higher for stability)
        
        # Recognition caching for performance
        self.recognition_cache = {}  # Cache recent recognition results
        self.cache_duration = 2.0  # Cache results for 2 seconds
        
        # Frame processing control with throttling - optimized for MobileFaceNet
        self.frame_skip_count = 5  # Process every 5th frame (improved from 10 for better responsiveness)
        self.current_frame_count = 0
        
        # Improved accuracy settings
        self.debug_distances = True  # Enable distance debugging
        
        # Background processing with Queue - optimized for lighter model
        self.processing_thread = None
        self.processing_active = False
        self.frame_queue = Queue(maxsize=1)  # Prevent frame backlog
        self.last_submission_time = 0
        self.submission_throttle = 0.5  # Reduced to 0.5 second for even faster processing
        self.latest_results = []
        self.results_lock = threading.Lock()
        
        logger.info(f"DeepFace Recognition System initialized with {model_name} model (MobileFaceNet), threshold: {self.threshold}")
        
        # Verify DeepFace installation and download models if needed
        self._verify_and_download_models()
    
    def _verify_and_download_models(self):
        """Verify DeepFace installation and download models if needed"""
        try:
            # Test DeepFace by creating a dummy embedding
            dummy_img = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
            temp_path = os.path.join(tempfile.gettempdir(), 'deepface_test.jpg')
            cv2.imwrite(temp_path, dummy_img)
            
            # This will download the model if not already present
            _ = DeepFace.represent(temp_path, model_name=self.model_name, enforce_detection=False)
            
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            logger.info(f"✅ {self.model_name} model verified and ready")
            
        except Exception as e:
            logger.error(f"❌ Error verifying DeepFace model: {e}")
            logger.info("Downloading models in background...")
    
    def extract_face_embedding_deepface_only(self, image_array: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        """
        Extract face embedding using pure DeepFace with better error handling
        
        Args:
            image_array: Input image as numpy array (BGR format from OpenCV)
            
        Returns:
            Tuple of (face_embedding, face_coordinates) or (None, None) if no face found
        """
        temp_path = None
        try:
            if image_array is None or image_array.size == 0:
                logger.debug("Empty or None image provided")
                return None, None
            
            # Create temporary file with unique name for thread safety
            temp_path = os.path.join(tempfile.gettempdir(), f'deepface_bg_{os.getpid()}_{threading.get_ident()}_{time.time():.3f}.jpg')
            
            # Save image to temporary file with error checking
            write_success = cv2.imwrite(temp_path, image_array)
            if not write_success:
                logger.error("Failed to write temporary image file")
                return None, None
            
            # Verify file was created and has size
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                logger.error("Temporary file creation failed or file is empty")
                return None, None
            
            # Profile DeepFace execution time
            start_time = time.time()
            logger.debug("Before DeepFace.represent()")
            
            # Use DeepFace for both detection and recognition with error handling
            embeddings = DeepFace.represent(
                img_path=temp_path,
                model_name=self.model_name,
                enforce_detection=False,  # Allow processing without strict face detection
                detector_backend=self.detector_backend
            )
            
            logger.debug("After DeepFace.represent()")
            execution_time = time.time() - start_time
            
            if execution_time > 3.0:
                logger.warning(f"DeepFace execution took {execution_time:.2f}s (very slow)")
            else:
                logger.debug(f"DeepFace execution time: {execution_time:.2f}s")
            
            if embeddings and len(embeddings) > 0:
                # Get the first embedding and facial area
                result = embeddings[0]
                embedding = np.array(result['embedding'])
                
                # Extract face coordinates if available
                face_coords = None
                if 'facial_area' in result:
                    area = result['facial_area']
                    face_coords = (area['x'], area['y'], area['w'], area['h'])
                
                logger.debug(f"Successfully extracted embedding with shape {embedding.shape}")
                return embedding, face_coords
            else:
                logger.debug("No faces detected by DeepFace")
                return None, None
                
        except Exception as e:
            logger.exception(f"DeepFace embedding extraction failed: {e}")
            return None, None
        finally:
            # Always clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as cleanup_e:
                    logger.warning(f"Failed to cleanup temp file {temp_path}: {cleanup_e}")
    
    def extract_face_embedding_hybrid(self, image_array: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        """
        Hybrid face extraction: Haar for detection + ArcFace for recognition
        
        Args:
            image_array: Input image as numpy array (BGR format from OpenCV)
            
        Returns:
            Tuple of (face_embedding, face_coordinates) or (None, None) if no face found
        """
        try:
            if image_array is None or image_array.size == 0:
                logger.debug("Empty or None image provided")
                return None, None
            
            # Step 1: Use Haar Cascade for fast face detection with optimized parameters
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
            
            # Apply histogram equalization to improve detection in varying lighting
            gray = cv2.equalizeHist(gray)
            
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.15,       # Slightly larger steps for faster detection
                minNeighbors=4,         # Reduced for faster processing with MobileFaceNet
                minSize=(50, 50),       # Slightly smaller minimum for better detection
                maxSize=(350, 350),     # Reduced maximum for faster processing
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            if len(faces) == 0:
                logger.debug("No faces detected by Haar Cascade")
                return None, None
            
            # Get the largest face (most prominent)
            largest_face = max(faces, key=lambda face: face[2] * face[3])
            x, y, w, h = largest_face
            
            logger.debug(f"Haar detected face at ({x}, {y}, {w}, {h})")
            
            # Step 2: Crop and preprocess the face region
            # Reduced padding for faster processing with MobileFaceNet
            padding = int(min(w, h) * 0.15)  # Reduced from 0.2 to 0.15
            x_start = max(0, x - padding)
            y_start = max(0, y - padding)
            x_end = min(image_array.shape[1], x + w + padding)
            y_end = min(image_array.shape[0], y + h + padding)
            
            face_crop = image_array[y_start:y_end, x_start:x_end]
            
            if face_crop.size == 0:
                logger.debug("Face crop is empty")
                return None, None
            
            # Step 3: Use DeepFace ArcFace to extract features from the cropped face
            temp_path = None
            try:
                # Save cropped face to temporary file for DeepFace
                temp_path = os.path.join(tempfile.gettempdir(), f'haar_crop_{os.getpid()}_{threading.get_ident()}_{time.time():.3f}.jpg')
                
                write_success = cv2.imwrite(temp_path, face_crop)
                if not write_success:
                    logger.error("Failed to write cropped face image")
                    return None, None
                
                # Extract features using ArcFace
                start_time = time.time()
                logger.debug(f"Extracting ArcFace features from Haar-detected face")
                
                embeddings = DeepFace.represent(
                    img_path=temp_path,
                    model_name=self.model_name,
                    enforce_detection=False,  # We already detected with Haar
                    detector_backend='skip'   # Skip DeepFace detection
                )
                
                execution_time = time.time() - start_time
                logger.debug(f"Hybrid ArcFace feature extraction took {execution_time:.2f}s")
                
                if embeddings and len(embeddings) > 0:
                    embedding = np.array(embeddings[0]['embedding'])
                    
                    # Return original Haar coordinates (adjusted back to full image)
                    face_coords = (x, y, w, h)
                    
                    logger.debug(f"Successfully extracted hybrid embedding with shape {embedding.shape}")
                    return embedding, face_coords
                else:
                    logger.debug("ArcFace failed to extract features from Haar-detected face")
                    return None, None
                    
            finally:
                # Always clean up temporary file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                        logger.debug(f"Cleaned up temp file: {temp_path}")
                    except Exception as cleanup_e:
                        logger.warning(f"Failed to cleanup temp file {temp_path}: {cleanup_e}")
                        
        except Exception as e:
            logger.exception(f"Hybrid face extraction failed: {e}")
            return None, None
    
    def load_known_faces(self, db_manager):
        """
        Load known face embeddings from database
        
        Args:
            db_manager: Database manager instance with get_all_employees method
        """
        try:
            employees = db_manager.get_all_employees()
            self.known_faces.clear()
            
            face_count = 0
            for employee in employees:
                if 'face_vector' in employee and employee['face_vector']:
                    # Convert face vector to numpy array
                    face_embedding = np.array(employee['face_vector'])
                    self.known_faces[employee['employee_id']] = {
                        'name': employee['name'],
                        'embedding': face_embedding
                    }
                    face_count += 1
                    logger.debug(f"Loaded face embedding for {employee['name']} ({employee['employee_id']})")
            
            logger.info(f"✅ Loaded {face_count} face embeddings from database")
            
        except Exception as e:
            logger.error(f"❌ Error loading known faces: {e}")
    
    def recognize_face(self, image_array: np.ndarray, confidence_threshold: float = None) -> Tuple[Optional[str], float]:
        """
        Recognize face in image against known faces
        
        Args:
            image_array: Input image as numpy array
            confidence_threshold: Override default threshold
            
        Returns:
            Tuple of (employee_id, confidence) or (None, 0.0) if no match
        """
        try:
            # Extract embedding from input image using hybrid approach
            face_embedding, face_coords = self.extract_face_embedding_hybrid(image_array)
            
            if face_embedding is None:
                logger.debug("No face detected for recognition")
                return None, 0.0
            
            if not self.known_faces:
                logger.warning("No known faces loaded")
                return None, 0.0
            
            threshold = confidence_threshold if confidence_threshold is not None else self.threshold
            best_match = None
            best_distance = float('inf')
            
            # Compare against all known faces
            for employee_id, face_data in self.known_faces.items():
                # Handle both simple embedding format and complex format
                if isinstance(face_data, dict):
                    known_embedding = face_data['embedding']
                else:
                    # Direct embedding format for simple testing
                    known_embedding = face_data
                
                # Calculate cosine similarity distance
                distance = self._calculate_distance(face_embedding, known_embedding)
                
                if self.debug_distances:
                    logger.info(f"Distance to {employee_id}: {distance:.3f}")
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = employee_id
            
            # Check if best match is within threshold
            if best_match and best_distance < threshold:
                confidence = max(0.0, 1.0 - best_distance)  # Convert distance to confidence
                
                # Get name if available
                if isinstance(self.known_faces[best_match], dict):
                    name = self.known_faces[best_match].get('name', best_match)
                else:
                    name = best_match
                    
                logger.info(f"Face recognized: {name} ({best_match}) with distance {best_distance:.3f}, confidence {confidence:.2f}")
                return best_match, confidence
            else:
                logger.info(f"No face match found - best: {best_match}, distance: {best_distance:.3f}, threshold: {threshold}")
                return None, 0.0
                
        except Exception as e:
            logger.error(f"Error recognizing face: {e}")
            return None, 0.0
    
    def _calculate_distance(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate distance between two face embeddings
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Distance value (lower = more similar)
        """
        try:
            # Normalize embeddings
            norm1 = embedding1 / np.linalg.norm(embedding1)
            norm2 = embedding2 / np.linalg.norm(embedding2)
            
            # Calculate cosine distance (1 - cosine similarity)
            cosine_similarity = np.dot(norm1, norm2)
            cosine_distance = 1 - cosine_similarity
            
            return cosine_distance
            
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return float('inf')
    
    def create_face_embedding_from_images(self, image_arrays: List[np.ndarray]) -> Optional[np.ndarray]:
        """
        Create averaged face embedding from multiple images for better accuracy
        
        Args:
            image_arrays: List of image arrays containing the same person's face
            
        Returns:
            Averaged face embedding or None if no valid embeddings found
        """
        try:
            valid_embeddings = []
            
            for i, image_array in enumerate(image_arrays):
                embedding, _ = self.extract_face_embedding(image_array)
                if embedding is not None:
                    valid_embeddings.append(embedding)
                    logger.debug(f"Valid embedding {i+1}/{len(image_arrays)} extracted")
                else:
                    logger.debug(f"No embedding found in image {i+1}/{len(image_arrays)}")
            
            if not valid_embeddings:
                logger.warning("No valid face embeddings found in any image")
                return None
            
            # Average the embeddings for better accuracy
            averaged_embedding = np.mean(valid_embeddings, axis=0)
            logger.info(f"Created averaged face embedding from {len(valid_embeddings)} images")
            
            return averaged_embedding
            
        except Exception as e:
            logger.error(f"Error creating face embedding from images: {e}")
            return None
    
    def start_background_processing(self):
        """Start background thread for face recognition processing"""
        if not self.processing_active:
            self.processing_active = True
            self.processing_thread = threading.Thread(target=self._background_processing_loop, daemon=True)
            self.processing_thread.start()
            logger.info("Background face processing started")
    
    def stop_background_processing(self):
        """Stop background thread for face recognition processing"""
        self.processing_active = False
        
        # Clear the queue to help thread exit faster
        try:
            while not self.frame_queue.empty():
                self.frame_queue.get_nowait()
                self.frame_queue.task_done()
        except:
            pass
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        logger.info("Background face processing stopped")
    
    def submit_frame_for_processing(self, frame: np.ndarray):
        """
        Submit a frame for background processing with throttling and queue management (non-blocking)
        
        Args:
            frame: Input frame to process
        """
        if not self.processing_active:
            logger.debug("Processing not active, skipping frame submission")
            return
            
        current_time = time.time()
        
        # Throttle submissions to prevent overwhelming the processing thread
        if (current_time - self.last_submission_time) >= self.submission_throttle:
            self.last_submission_time = current_time
            
            # Check if queue is full and clear it if needed (prevent backlog)
            if self.frame_queue.full():
                try:
                    # Remove old frame if queue is full
                    self.frame_queue.get_nowait()
                    logger.debug("Queue was full, removed old frame")
                except:
                    pass
            
            try:
                # Submit new frame (make a copy to prevent threading issues)
                frame_copy = frame.copy()
                self.frame_queue.put_nowait(frame_copy)
                logger.debug("Frame submitted to processing queue")
            except Exception as e:
                logger.debug(f"Failed to submit frame: {e}")
        else:
            # Log throttling occasionally
            time_since_last = current_time - self.last_submission_time
            remaining_throttle = self.submission_throttle - time_since_last
            if int(current_time) % 5 == 0:  # Log every 5 seconds
                logger.debug(f"Frame submission throttled, {remaining_throttle:.1f}s remaining")
    
    def get_latest_results(self) -> List[dict]:
        """
        Get latest recognition results (non-blocking)
        
        Returns:
            List of face recognition results
        """
        with self.results_lock:
            return self.latest_results.copy()
    
    def clear_latest_results(self):
        """
        Clear cached recognition results (useful when camera stops)
        """
        with self.results_lock:
            self.latest_results = []
            logger.debug("Recognition results cache cleared")
    
    def _background_processing_loop(self):
        """Background thread loop for processing frames using Queue"""
        # Initialize CPU monitoring for this thread
        process = psutil.Process()
        last_cpu_log = 0
        
        logger.info("[THREAD] Background processing thread started")
        
        while self.processing_active:
            try:
                # Monitor CPU usage every 10 seconds or if high
                current_time = time.time()
                if current_time - last_cpu_log > 10:
                    cpu_percent = process.cpu_percent()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    
                    # Force garbage collection and log memory status
                    collected = gc.collect()
                    logger.info(f"[CPU MONITOR] Background Recognition: CPU={cpu_percent:.1f}%, Memory={memory_mb:.1f}MB")
                    if collected > 0:
                        logger.info(f"[GC] Collected {collected} objects")
                    last_cpu_log = current_time
                
                logger.debug("[THREAD] Waiting for frame from queue...")
                
                # Wait for a frame with timeout to allow clean shutdown
                frame = self.frame_queue.get(timeout=1.0)
                
                logger.debug("[THREAD] Got frame, starting DeepFace processing...")
                
                # Perform face recognition with detailed logging
                start_time = time.time()
                logger.debug("[THREAD] Before DeepFace processing")
                
                results = self._process_frame_hybrid(frame)
                
                logger.debug("[THREAD] After DeepFace processing")
                processing_time = time.time() - start_time
                
                # Log if processing takes too long
                if processing_time > 2.0:
                    logger.warning(f"[PERFORMANCE] Slow face processing: {processing_time:.2f}s")
                else:
                    logger.debug(f"[PERFORMANCE] Frame processed in {processing_time:.2f}s")
                
                # Update results thread-safely
                logger.debug("[THREAD] Updating results...")
                with self.results_lock:
                    self.latest_results = results
                logger.debug("[THREAD] Results updated successfully")
                
            except Empty:
                # Normal timeout - no frame available, continue looping
                logger.debug("[THREAD] Queue timeout, continuing...")
                continue
            except Exception as e:
                if self.processing_active:  # Only log if we're supposed to be running
                    logger.exception(f"[THREAD ERROR] Uncaught exception in background processing: {e}")
                    # Force garbage collection on error
                    collected = gc.collect()
                    logger.info(f"[GC ERROR] Collected {collected} objects after error")
                time.sleep(0.5)  # Brief delay on errors
        
        logger.info("[THREAD] Background processing thread stopped")
    
    def _process_frame_pure_deepface(self, frame: np.ndarray) -> List[dict]:
        """
        Process frame using pure DeepFace (internal method)
        
        Args:
            frame: Input frame to process
            
        Returns:
            List of face detection/recognition results
        """
        try:
            results = []
            
            # Use pure DeepFace for detection and recognition
            face_embedding, face_coords = self.extract_face_embedding_deepface_only(frame)
            
            if face_embedding is not None:
                # Try to recognize the face
                best_match = None
                best_distance = float('inf')
                best_name = None
                
                if self.known_faces:
                    for employee_id, face_data in self.known_faces.items():
                        known_embedding = face_data['embedding'] if isinstance(face_data, dict) else face_data
                        distance = self._calculate_distance(face_embedding, known_embedding)
                        
                        if distance < best_distance:
                            best_distance = distance
                            best_match = employee_id
                            if isinstance(face_data, dict):
                                best_name = face_data.get('name', employee_id)
                            else:
                                best_name = employee_id
                
                # Create result
                if best_match and best_distance < self.threshold:
                    confidence = max(0.0, 1.0 - best_distance)
                    logger.debug(f"Face recognized in background: {best_name} ({best_match}) with distance {best_distance:.3f}, confidence {confidence:.2f}")
                    results.append({
                        'employee_id': best_match,
                        'name': best_name,
                        'confidence': confidence,
                        'position': face_coords or (0, 0, 100, 100)  # Default if no coords
                    })
                else:
                    # Unknown face
                    logger.debug(f"Unknown face in background - best: {best_match}, distance: {best_distance:.3f}, threshold: {self.threshold}")
                    results.append({
                        'employee_id': None,
                        'name': None,
                        'confidence': 0.0,
                        'position': face_coords or (0, 0, 100, 100)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing frame with pure DeepFace: {e}")
            return []
    
    def _process_frame_hybrid(self, frame: np.ndarray) -> List[dict]:
        """
        Process frame using hybrid approach: Haar detection + ArcFace recognition
        
        Args:
            frame: Input frame to process
            
        Returns:
            List of face detection/recognition results
        """
        try:
            results = []
            
            # Use hybrid approach for detection and recognition
            face_embedding, face_coords = self.extract_face_embedding_hybrid(frame)
            
            if face_embedding is not None:
                # Try to recognize the face
                best_match = None
                best_distance = float('inf')
                best_name = None
                
                if self.known_faces:
                    for employee_id, face_data in self.known_faces.items():
                        known_embedding = face_data['embedding'] if isinstance(face_data, dict) else face_data
                        distance = self._calculate_distance(face_embedding, known_embedding)
                        
                        if distance < best_distance:
                            best_distance = distance
                            best_match = employee_id
                            if isinstance(face_data, dict):
                                best_name = face_data.get('name', employee_id)
                            else:
                                best_name = employee_id
                
                # Create result
                if best_match and best_distance < self.threshold:
                    confidence = max(0.0, 1.0 - best_distance)
                    logger.debug(f"Hybrid recognition: {best_name} ({best_match}) with distance {best_distance:.3f}, confidence {confidence:.2f}")
                    results.append({
                        'employee_id': best_match,
                        'name': best_name,
                        'confidence': confidence,
                        'position': face_coords or (0, 0, 100, 100)  # Default if no coords
                    })
                else:
                    # Unknown face
                    logger.debug(f"Unknown face (hybrid) - best: {best_match}, distance: {best_distance:.3f}, threshold: {self.threshold}")
                    if face_coords:
                        results.append({
                            'employee_id': None,
                            'name': 'Unknown',
                            'confidence': 0.0,
                            'position': face_coords
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in hybrid frame processing: {e}")
            return []
    
    def recognize_face_simple(self, image_array: np.ndarray, confidence_threshold: float = None) -> Tuple[Optional[str], float]:
        """
        Simple face recognition for single face detection (for compatibility)
        
        Args:
            image_array: Input image as numpy array
            confidence_threshold: Override default threshold
            
        Returns:
            Tuple of (employee_id, confidence) or (None, 0.0) if no match
        """
        try:
            face_embedding, _ = self.extract_face_embedding_hybrid(image_array)
            
            if face_embedding is None:
                return None, 0.0
            
            if not self.known_faces:
                logger.warning("No known faces loaded")
                return None, 0.0
            
            threshold = confidence_threshold if confidence_threshold is not None else self.threshold
            best_match = None
            best_distance = float('inf')
            
            # Compare against all known faces
            for employee_id, face_data in self.known_faces.items():
                known_embedding = face_data['embedding'] if isinstance(face_data, dict) else face_data
                distance = self._calculate_distance(face_embedding, known_embedding)
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = employee_id
            
            # Check if best match is within threshold
            if best_match and best_distance < threshold:
                confidence = max(0.0, 1.0 - best_distance)
                logger.info(f"Face recognized: {best_match} with confidence {confidence:.2f}")
                return best_match, confidence
            else:
                logger.debug(f"No face match found (best distance: {best_distance:.2f}, threshold: {threshold})")
                return None, 0.0
                
        except Exception as e:
            logger.error(f"Error recognizing face: {e}")
            return None, 0.0
    
    def draw_face_boxes_from_results(self, image_array: np.ndarray, results: List[dict]) -> np.ndarray:
        """
        Draw bounding boxes around detected faces with recognition results
        
        Args:
            image_array: Input image as numpy array
            results: List of recognition results with position info
            
        Returns:
            Image with face boxes and labels drawn
        """
        try:
            if image_array is None or image_array.size == 0:
                return image_array
            
            result_image = image_array.copy()
            
            for result in results:
                if 'position' in result:
                    x, y, w, h = result['position']
                    name = result.get('name', 'Unknown')
                    confidence = result.get('confidence', 0.0)
                    
                    # Choose color and label based on recognition status
                    if name == 'Low Confidence':
                        color = (0, 165, 255)  # Orange for low confidence detections
                        label = f"Low Confidence ({confidence:.1f}%)"
                    elif name and name != 'Unknown':
                        color = (0, 255, 0)  # Green for recognized
                        label = f"{name} ({confidence:.1f}%)"
                    else:
                        color = (0, 255, 255)  # Yellow for detected but not recognized
                        label = "Unknown Face"
                    
                    # Draw rectangle
                    cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
                    
                    # Draw label background
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                    cv2.rectangle(result_image, (x, y - 25), (x + label_size[0], y), color, -1)
                    
                    # Draw label text
                    cv2.putText(result_image, label, (x, y - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            return result_image
            
        except Exception as e:
            logger.error(f"Error drawing face boxes: {e}")
    def get_face_detection_info(self) -> dict:
        """Get information about the face detection system"""
        return {
            'model_name': self.model_name,
            'detector_backend': self.detector_backend,
            'threshold': self.threshold,
            'known_faces_count': len(self.known_faces),
            'target_size': self.target_size
        }
    
    def detect_faces_fast(self, image_array: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Fast face detection using background DeepFace results for smooth video preview
        Use this for live video display, not for recognition
        
        Args:
            image_array: Input image as numpy array (BGR format from OpenCV)
            
        Returns:
            List of face coordinates as (x, y, w, h) tuples
        """
        try:
            if image_array is None or image_array.size == 0:
                return []
            
            # Use background processing results for consistent detection
            results = self.get_latest_results()
            if results and 'faces' in results:
                return results['faces']
            return []
            
        except Exception as e:
            logger.error(f"Error in fast face detection: {e}")
            return []
    
    def draw_face_boxes(self, image_array: np.ndarray, faces: List[Tuple[int, int, int, int]], recognized_names: List[str] = None, color=(0, 255, 0), thickness=2) -> np.ndarray:
        """
        Draw bounding boxes around detected faces with recognition results
        
        Args:
            image_array: Input image as numpy array
            faces: List of face coordinates as (x, y, w, h) tuples
            recognized_names: List of recognized names corresponding to faces
            color: Box color in BGR format
            thickness: Box line thickness
            
        Returns:
            Image with face boxes and labels drawn
        """
        try:
            if image_array is None:
                return image_array
                
            result_image = image_array.copy()
            
            for i, (x, y, w, h) in enumerate(faces):
                # Determine label and color
                if recognized_names and i < len(recognized_names) and recognized_names[i]:
                    label = recognized_names[i]
                    box_color = (0, 255, 0)  # Green for recognized faces
                    label_color = (0, 255, 0)
                else:
                    label = "UNKNOWN"
                    box_color = (0, 255, 255)  # Yellow for unrecognized faces
                    label_color = (0, 255, 255)
                
                # Draw rectangle around face
                cv2.rectangle(result_image, (x, y), (x + w, y + h), box_color, thickness)
                
                # Add label with background for better readability
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, thickness)[0]
                cv2.rectangle(result_image, (x, y - label_size[1] - 10), 
                             (x + label_size[0], y), box_color, -1)
                cv2.putText(result_image, label, (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), thickness)
            
            return result_image
            
        except Exception as e:
            logger.error(f"Error drawing face boxes: {e}")
            return image_array


class CameraManager:
    """
    Camera management for face recognition system
    """
    
    def __init__(self, camera_index=0):
        """Initialize camera manager"""
        self.camera_index = camera_index
        self.cap = None
        self.is_active = False
        
    def start_camera(self):
        """Start camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                # Set camera properties for better performance and higher FPS
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 60)  # Increased from 30 to 60 FPS for smoother video
                
                # Additional optimizations for smoother capture and reduced latency
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer size to minimize latency
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)   # Enable autofocus
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # Enable auto exposure
                
                # Try to set fourcc for better performance (if supported)
                try:
                    self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                except:
                    pass  # Ignore if not supported
                
                self.is_active = True
                logger.info("✅ Camera started successfully")
                return True
            else:
                logger.error("❌ Failed to open camera")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop camera capture"""
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
            self.is_active = False
            logger.info("📷 Camera stopped")
            
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
    
    def read_frame(self):
        """Read frame from camera"""
        if self.cap and self.is_active:
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None
