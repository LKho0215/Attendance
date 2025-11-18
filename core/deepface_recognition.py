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
    
    def __init__(self, model_name='ArcFace', detector_backend='opencv'):
        self.model_name = model_name
        self.detector_backend = detector_backend
        self.known_faces = {}  
        self.debug_distances = True  # Enable distance debugging
        
        # Initialize Haar Cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        logger.info("✅ Haar Cascade face detector loaded")
        
        # DeepFace model settings - optimized for MobileFaceNet
        self.target_size = (160, 160)  # MobileFaceNet input size (smaller than ArcFace)
        self.threshold = 0.50  # Much more strict threshold - reduced from 0.68 to 0.50 for higher accuracy
        self.distance_threshold = 0.40  # Increased from 0.25 to 0.50 for better recognition while maintaining security
        
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
        
        logger.info(f"DeepFace Recognition System initialized with {model_name} model (ArcFace - State-of-the-art), threshold: {self.threshold}")
        
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
        try:
            # Load face vectors from database
            employees_with_vectors = db_manager.get_all_face_vectors()
            self.known_faces.clear()
            
            if employees_with_vectors:
                face_count = 0
                total_vectors = 0
                
                for employee in employees_with_vectors:
                    username = employee['username']
                    employee_name = employee['name']
                    
                    if 'face_vectors' in employee and employee['face_vectors']:
                        face_vectors_list = employee['face_vectors']
                        
                        if isinstance(face_vectors_list, list) and len(face_vectors_list) > 0:
                            embeddings = []
                            
                            for i, vector in enumerate(face_vectors_list):
                                if vector and isinstance(vector, list):
                                    try:
                                        # Convert simple array to numpy array
                                        embedding = np.array(vector, dtype=np.float32)
                                        
                                        # Verify vector has 512 dimensions
                                        if embedding.shape == (512,):
                                            embeddings.append(embedding)
                                            logger.debug(f"Loaded vector {i} for {employee_name} (shape: {embedding.shape})")
                                        else:
                                            logger.warning(f"Invalid vector shape for {employee_name}[{i}]: {embedding.shape}, expected (512,)")
                                    except Exception as e:
                                        logger.warning(f"Failed to convert vector {i} for {employee_name}: {e}")
                            
                            # Store if we have valid embeddings
                            if embeddings:
                                # Also store the nric to be returned by recognize_face
                                nric = employee.get('nric', username)
                                self.known_faces[username] = {
                                    'name': employee_name,
                                    'embeddings': embeddings,
                                    'nric': nric  # Store NRIC separately
                                }
                                face_count += 1
                                total_vectors += len(embeddings)
                                logger.info(f"✅ Loaded {len(embeddings)} face vectors for {employee_name} ({username}, NRIC: {nric})")
                            else:
                                logger.warning(f"No valid face vectors found for {employee_name} ({username})")
                        else:
                            logger.debug(f"No face_vectors list found for {employee_name} ({username})")
                    else:
                        logger.debug(f"No face_vectors field found for {employee_name} ({username})")

                if face_count > 0:
                    logger.info(f"✅ Successfully loaded {total_vectors} face vectors for {face_count} employees")
                else:
                    logger.warning("⚠️  No valid face vectors found in database")
                    
            else:
                logger.warning("⚠️  No employees with face vectors found in database")
            
        except Exception as e:
            logger.error(f"❌ Error loading known faces: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Clear known faces on error to prevent issues
            self.known_faces.clear()
    
    def recognize_face(self, image_array: np.ndarray, confidence_threshold: float = None) -> Tuple[Optional[str], float]:
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
            best_confidence = 0.0
            
            # Compare against all known faces - now supporting multiple vectors per employee
            for username, face_data in self.known_faces.items():
                # Handle new format with multiple embeddings
                if isinstance(face_data, dict) and 'embeddings' in face_data:
                    known_embeddings = face_data['embeddings']
                    employee_name = face_data.get('name', username)

                    # Compare against ALL stored vectors for this employee
                    min_distance = float('inf')
                    for i, known_embedding in enumerate(known_embeddings):
                        # Calculate cosine similarity distance
                        distance = self._calculate_distance(face_embedding, known_embedding)
                        
                        if self.debug_distances:
                            logger.info(f"Distance to {username}[{i}]: {distance:.3f}")

                        # Keep track of the minimum distance for this employee
                        if distance < min_distance:
                            min_distance = distance
                    
                    # Use the best (minimum) distance for this employee
                    if min_distance < best_distance:
                        best_distance = min_distance
                        best_match = username
                        best_confidence = max(0.0, 1.0 - min_distance)
                        
                    if self.debug_distances:
                        nric_value = face_data.get('nric', 'N/A')
                        logger.info(f"Best distance for {username} (NRIC: {nric_value}): {min_distance:.3f} (from {len(known_embeddings)} vectors)")

                # Handle legacy format (single embedding) for backward compatibility
                elif isinstance(face_data, dict) and 'embedding' in face_data:
                    known_embedding = face_data['embedding']
                    distance = self._calculate_distance(face_embedding, known_embedding)
                    
                    if self.debug_distances:
                        logger.info(f"Distance to {username} (legacy): {distance:.3f}")
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_match = username
                        best_confidence = max(0.0, 1.0 - distance)
                
                # Handle direct embedding format for simple testing
                else:
                    known_embedding = face_data
                    distance = self._calculate_distance(face_embedding, known_embedding)
                    
                    if self.debug_distances:
                        logger.info(f"Distance to {username} (direct): {distance:.3f}")

                    if distance < best_distance:
                        best_distance = distance
                        best_match = username
                        best_confidence = max(0.0, 1.0 - distance)
            
            # Check if best match is within threshold
            if best_match and best_distance < self.distance_threshold:
                try:
                    # Store the username for later use
                    original_username = best_match
                    employee_name = original_username  # Default name
                    
                    # Handle different data structures for known faces
                    if isinstance(self.known_faces[original_username], dict):
                        face_data = self.known_faces[original_username]
                        
                        # Get the NRIC if available
                        if 'nric' in face_data:
                            best_match = face_data['nric']  # Replace username with NRIC
                            logger.debug(f"Using NRIC '{best_match}' for username '{original_username}'")
                        
                        # Get the employee name
                        if 'name' in face_data:
                            employee_name = face_data['name']
                        
                        # Get the embedding for dimension check
                        if 'embeddings' in face_data and face_data['embeddings']:
                            known_embedding = face_data['embeddings'][0]
                        elif 'embedding' in face_data:
                            known_embedding = face_data['embedding']
                        else:
                            known_embedding = None
                            logger.warning(f"No embeddings found for {original_username}")
                    else:
                        # Direct embedding storage (legacy format)
                        known_embedding = self.known_faces[original_username]
                        
                except Exception as e:
                    logger.error(f"Error accessing face data: {e}")
                    # Keep original values if there was an error
                    best_match = original_username  # Revert to username
                    employee_name = original_username
                    known_embedding = None
                
                # Check dimension compatibility
                if known_embedding is None:
                    logger.warning(f"No valid embedding found for {best_match}")
                    return None, 0.0
                elif len(face_embedding) != len(known_embedding):
                    logger.warning(f"Dimension mismatch: current={len(face_embedding)}, stored={len(known_embedding)}. Skipping {best_match}.")
                    logger.info("💡 Please re-register employees after model upgrade for better accuracy")
                    return None, 0.0
                
                # Additional confidence check - reject low confidence matches
                if best_confidence < 0.65:  # Reduced from 0.75 to 0.70 since multiple vectors provide better accuracy
                    logger.info(f"Recognition confidence too low: {best_confidence:.2f} < 0.65 for {best_match}")
                    return None, 0.0
                
                logger.info(f"Face recognized: {employee_name} ({best_match}) with distance {best_distance:.3f}, confidence {best_confidence:.2f}")
                return best_match, best_confidence
            else:
                if best_match:
                    logger.info(f"Face match found but distance too high: {best_match}, distance: {best_distance:.3f}, threshold: {self.distance_threshold}")
                else:
                    logger.info(f"No face match found in {len(self.known_faces)} known faces")
                return None, 0.0
                
        except Exception as e:
            logger.error(f"Error recognizing face: {e}")
            return None, 0.0
    
    def _calculate_distance(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        try:
            if len(embedding1) != len(embedding2):
                logger.warning(f"Embedding dimension mismatch: {len(embedding1)} vs {len(embedding2)}")
                return float('inf')  # Return maximum distance for incompatible embeddings
            
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
    
    def extract_multiple_face_embeddings(self, image_array: np.ndarray, num_extractions: int = 5) -> List[np.ndarray]:
        embeddings = []
        
        try:
            for i in range(num_extractions):
                # Add slight variations to improve robustness
                if i == 0:
                    # Original image
                    processed_img = image_array
                elif i == 1:
                    # Slightly enhance contrast
                    processed_img = cv2.convertScaleAbs(image_array, alpha=1.1, beta=10)
                elif i == 2:
                    # Slight gaussian blur to reduce noise
                    processed_img = cv2.GaussianBlur(image_array, (3, 3), 0.5)
                elif i == 3:
                    # Histogram equalization
                    if len(image_array.shape) == 3:
                        processed_img = cv2.cvtColor(image_array, cv2.COLOR_BGR2YUV)
                        processed_img[:,:,0] = cv2.equalizeHist(processed_img[:,:,0])
                        processed_img = cv2.cvtColor(processed_img, cv2.COLOR_YUV2BGR)
                    else:
                        processed_img = cv2.equalizeHist(image_array)
                else:
                    # Minor rotation and resize variations
                    h, w = image_array.shape[:2]
                    center = (w // 2, h // 2)
                    angle = (-2 + i) * 0.5  # Very small rotations
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    processed_img = cv2.warpAffine(image_array, M, (w, h))
                
                # Extract embedding
                embedding, _ = self.extract_face_embedding_hybrid(processed_img)
                
                if embedding is not None:
                    embeddings.append(embedding)
                    logger.debug(f"Extracted embedding {i+1}/{num_extractions} successfully")
                
            logger.info(f"Extracted {len(embeddings)}/{num_extractions} valid embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error extracting multiple embeddings: {e}")
            return []

    def create_robust_face_embedding(self, image_arrays: List[np.ndarray]) -> Optional[np.ndarray]:
        try:
            all_embeddings = []
            
            # Extract multiple embeddings from each image
            for i, image_array in enumerate(image_arrays):
                embeddings = self.extract_multiple_face_embeddings(image_array, num_extractions=3)
                all_embeddings.extend(embeddings)
                logger.debug(f"Image {i+1}/{len(image_arrays)} contributed {len(embeddings)} embeddings")
            
            if len(all_embeddings) < 3:
                logger.warning(f"Only {len(all_embeddings)} embeddings extracted, minimum 3 required")
                return None
            
            # Convert to numpy array for processing
            embeddings_array = np.array(all_embeddings)
            
            # Calculate pairwise cosine distances to identify outliers using numpy
            def cosine_distance_matrix(embeddings):
                """Calculate cosine distance matrix using numpy"""
                # Normalize embeddings
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                normalized_embeddings = embeddings / norms
                
                # Calculate cosine similarity matrix
                similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)
                
                # Convert to distance matrix (1 - similarity)
                distance_matrix = 1 - similarity_matrix
                return distance_matrix
            
            distances = cosine_distance_matrix(embeddings_array)
            
            # Calculate mean distance for each embedding to all others
            mean_distances = np.mean(distances, axis=1)
            
            # Remove outliers (embeddings with distance > 1.5 * std from mean)
            threshold = np.mean(mean_distances) + 1.5 * np.std(mean_distances)
            valid_indices = mean_distances < threshold
            
            filtered_embeddings = embeddings_array[valid_indices]
            
            if len(filtered_embeddings) < 2:
                logger.warning("Too many outliers removed, using all embeddings")
                filtered_embeddings = embeddings_array
            
            # Calculate robust average using median for better outlier resistance
            robust_embedding = np.median(filtered_embeddings, axis=0)
            
            logger.info(f"Created robust embedding from {len(filtered_embeddings)}/{len(all_embeddings)} valid embeddings")
            
            return robust_embedding
            
        except Exception as e:
            logger.error(f"Error creating robust embedding: {e}")
            return None

    def create_face_embedding_from_images(self, image_arrays: List[np.ndarray]) -> Optional[np.ndarray]:
        return self.create_robust_face_embedding(image_arrays)
    
    def start_background_processing(self):
        if not self.processing_active:
            self.processing_active = True
            self.processing_thread = threading.Thread(target=self._background_processing_loop, daemon=True)
            self.processing_thread.start()
            logger.info("Background face processing started")
    
    def stop_background_processing(self):
        self.processing_active = False
        
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

        with self.results_lock:
            return self.latest_results.copy()
    
    def clear_latest_results(self):

        with self.results_lock:
            self.latest_results = []
            logger.debug("Recognition results cache cleared")
    
    def _background_processing_loop(self):
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
                    for username, face_data in self.known_faces.items():
                        known_embedding = face_data['embedding'] if isinstance(face_data, dict) else face_data
                        distance = self._calculate_distance(face_embedding, known_embedding)
                        
                        if distance < best_distance:
                            best_distance = distance
                            best_match = username
                            if isinstance(face_data, dict):
                                best_name = face_data.get('name', username)
                            else:
                                best_name = username

                # Create result
                if best_match and best_distance < self.distance_threshold:  # Use stricter distance_threshold
                    confidence = max(0.0, 1.0 - best_distance)
                    
                    # Additional confidence check - reject low confidence matches
                    if confidence < 0.75:  # Slightly relaxed from 0.80 to 0.75 for better usability
                        logger.debug(f"Background recognition confidence too low: {confidence:.2f} < 0.75 for {best_match}")
                        # Treat as unknown face
                        results.append({
                            'username': None,
                            'name': None,
                            'confidence': 0.0,
                            'position': face_coords or (0, 0, 100, 100)
                        })
                    else:
                        logger.debug(f"Face recognized in background: {best_name} ({best_match}) with distance {best_distance:.3f}, confidence {confidence:.2f}")
                        results.append({
                            'username': best_match,
                            'name': best_name,
                            'confidence': confidence,
                            'position': face_coords or (0, 0, 100, 100)  # Default if no coords
                        })
                else:
                    # Unknown face
                    logger.debug(f"Unknown face in background - best: {best_match}, distance: {best_distance:.3f}, threshold: {self.distance_threshold}")
                    results.append({
                        'username': None,
                        'name': None,
                        'confidence': 0.0,
                        'position': face_coords or (0, 0, 100, 100)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing frame with pure DeepFace: {e}")
            return []
    
    def _process_frame_hybrid(self, frame: np.ndarray) -> List[dict]:
        try:
            results = []
            
            # Use hybrid approach for detection and recognition
            face_embedding, face_coords = self.extract_face_embedding_hybrid(frame)
            
            if face_embedding is not None:
                # Try to recognize the face using multiple vectors comparison
                best_match = None
                best_distance = float('inf')
                best_name = None
                
                if self.known_faces:
                    for username, face_data in self.known_faces.items():
                        # Handle new format with multiple embeddings
                        if isinstance(face_data, dict) and 'embeddings' in face_data:
                            known_embeddings = face_data['embeddings']
                            employee_name = face_data.get('name', username)

                            # Compare against ALL stored vectors for this employee
                            min_distance = float('inf')
                            for known_embedding in known_embeddings:
                                distance = self._calculate_distance(face_embedding, known_embedding)
                                if distance < min_distance:
                                    min_distance = distance
                            
                            # Use the best (minimum) distance for this employee
                            if min_distance < best_distance:
                                best_distance = min_distance
                                best_match = username
                                best_name = employee_name
                        
                        # Handle legacy format for backward compatibility
                        elif isinstance(face_data, dict) and 'embedding' in face_data:
                            known_embedding = face_data['embedding']
                            distance = self._calculate_distance(face_embedding, known_embedding)
                            if distance < best_distance:
                                best_distance = distance
                                best_match = username
                                best_name = face_data.get('name', username)

                        # Handle direct embedding format
                        else:
                            known_embedding = face_data
                            distance = self._calculate_distance(face_embedding, known_embedding)
                            if distance < best_distance:
                                best_distance = distance
                                best_match = username
                                best_name = username

                # Create result
                if best_match and best_distance < self.distance_threshold:  # Use stricter distance_threshold
                    confidence = max(0.0, 1.0 - best_distance)
                    logger.debug(f"Hybrid recognition: {best_name} ({best_match}) with distance {best_distance:.3f}, confidence {confidence:.2f}")
                    results.append({
                        'username': best_match,
                        'name': best_name,
                        'confidence': confidence,
                        'position': face_coords or (0, 0, 100, 100)  # Default if no coords
                    })
                else:
                    # Unknown face
                    logger.debug(f"Unknown face (hybrid) - best: {best_match}, distance: {best_distance:.3f}, threshold: {self.distance_threshold}")
                    if face_coords:
                        results.append({
                            'username': None,
                            'name': 'Unknown',
                            'confidence': 0.0,
                            'position': face_coords
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in hybrid frame processing: {e}")
            return []
    
    def draw_face_boxes_from_results(self, image_array: np.ndarray, results: List[dict]) -> np.ndarray:
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
