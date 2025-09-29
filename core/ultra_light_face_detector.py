"""
Ultra Lightweight Face Detection using OpenVINO
Achieving 100+ FPS on CPU with minimal memory usage

Based on the Ultra-lightweight Face Detection RFB 320 model
"""
import cv2
import numpy as np
import time
from typing import List, Tuple, Optional
import requests
import os
from pathlib import Path

try:
    from openvino.runtime import Core, Model
    OPENVINO_AVAILABLE = True
except ImportError:
    print("OpenVINO not available. Please install with: pip install openvino")
    OPENVINO_AVAILABLE = False


class UltraLightFaceDetector:
    """Ultra-lightweight face detector using OpenVINO for maximum performance"""
    
    def __init__(self, 
                 model_path: Optional[str] = None,
                 confidence_threshold: float = 0.7,
                 nms_threshold: float = 0.5,
                 input_size: Tuple[int, int] = (320, 240)):
        """
        Initialize the Ultra Light Face Detector
        
        Args:
            model_path: Path to the OpenVINO IR model (.xml file)
            confidence_threshold: Minimum confidence for face detection
            nms_threshold: Non-maximum suppression threshold
            input_size: Model input size (width, height)
        """
        if not OPENVINO_AVAILABLE:
            raise ImportError("OpenVINO is required for UltraLightFaceDetector")
        
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size  # (width, height)
        
        # Model URLs and paths
        self.model_dir = Path(__file__).parent.parent / "models" / "ultra-lightweight-face-detection-rfb-320"
        self.model_xml = self.model_dir / "ultra-lightweight-face-detection-rfb-320.xml"
        self.model_bin = self.model_dir / "ultra-lightweight-face-detection-rfb-320.bin"
        
        # Initialize OpenVINO
        self.core = Core()
        self.model = None
        self.compiled_model = None
        self.input_layer = None
        self.output_layers = None
        
        # Performance tracking
        self.last_fps = 0
        self.frame_count = 0
        self.start_time = time.time()
        
        # Download and load model
        self._setup_model(model_path)
        
        print(f"[ULTRA LIGHT] Face detector initialized")
        print(f"[ULTRA LIGHT] Input size: {self.input_size}")
        print(f"[ULTRA LIGHT] Confidence threshold: {self.confidence_threshold}")
        print(f"[ULTRA LIGHT] NMS threshold: {self.nms_threshold}")
    
    def _setup_model(self, model_path: Optional[str] = None):
        """Setup the OpenVINO model"""
        # First try to use OpenVINO IR format
        if model_path and os.path.exists(model_path):
            model_xml = model_path
        elif self.model_xml.exists():
            model_xml = str(self.model_xml)
        else:
            model_xml = None
        
        if model_xml:
            try:
                # Load OpenVINO IR model
                print(f"[ULTRA LIGHT] Loading OpenVINO IR model from: {model_xml}")
                self.model = self.core.read_model(model_xml)
                self.compiled_model = self.core.compile_model(self.model, "CPU")
                
                # Get input and output layers
                self.input_layer = self.compiled_model.input(0)
                self.output_layers = {
                    'boxes': None,
                    'scores': None
                }
                
                # Identify output layers (boxes and scores)
                for output in self.compiled_model.outputs:
                    output_shape = output.get_shape()
                    if len(output_shape) == 3 and output_shape[2] == 4:
                        self.output_layers['boxes'] = output
                        print(f"[ULTRA LIGHT] Boxes output: {output.get_any_name()}, shape: {output_shape}")
                    elif len(output_shape) == 3 and output_shape[2] == 2:
                        self.output_layers['scores'] = output
                        print(f"[ULTRA LIGHT] Scores output: {output.get_any_name()}, shape: {output_shape}")
                
                if not all(self.output_layers.values()):
                    raise ValueError("Could not identify model outputs")
                
                print("[ULTRA LIGHT] OpenVINO IR model loaded successfully!")
                return
                
            except Exception as e:
                print(f"[ULTRA LIGHT] OpenVINO IR model failed: {e}")
                print("[ULTRA LIGHT] Falling back to ONNX model...")
        
        # Fallback to ONNX model
        self._download_model()
    
    def _download_model(self):
        """Download the model files if they don't exist"""
        print("[ULTRA LIGHT] Setting up ONNX model...")
        
        # Create model directory
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Download ONNX model directly from the source
        onnx_url = "https://github.com/Linzaer/Ultra-Light-Fast-Generic-Face-Detector-1MB/raw/master/models/onnx/version-RFB-320.onnx"
        onnx_path = self.model_dir / "ultra-lightweight-face-detection-rfb-320.onnx"
        
        try:
            if not onnx_path.exists():
                print(f"[ULTRA LIGHT] Downloading ONNX model from: {onnx_url}")
                response = requests.get(onnx_url, stream=True)
                response.raise_for_status()
                
                with open(onnx_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"[ULTRA LIGHT] Downloaded ONNX model to: {onnx_path}")
            
            # Use OpenCV DNN as implementation
            self._setup_opencv_fallback(str(onnx_path))
            
        except Exception as e:
            print(f"[ULTRA LIGHT ERROR] Failed to setup ONNX model: {e}")
            raise RuntimeError("Could not set up face detection model")
    
    def _create_fallback_model(self):
        """Create a fallback using OpenCV DNN as alternative"""
        print("[ULTRA LIGHT] Creating OpenCV DNN fallback...")
        
        # Download ONNX model directly from the source
        onnx_url = "https://github.com/Linzaer/Ultra-Light-Fast-Generic-Face-Detector-1MB/raw/master/models/onnx/version-RFB-320.onnx"
        onnx_path = self.model_dir / "ultra-lightweight-face-detection-rfb-320.onnx"
        
        try:
            if not onnx_path.exists():
                print(f"[ULTRA LIGHT] Downloading ONNX model from: {onnx_url}")
                response = requests.get(onnx_url, stream=True)
                response.raise_for_status()
                
                with open(onnx_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"[ULTRA LIGHT] Downloaded ONNX model to: {onnx_path}")
            
            # Use OpenCV DNN as fallback
            self._setup_opencv_fallback(str(onnx_path))
            
        except Exception as e:
            print(f"[ULTRA LIGHT ERROR] Failed to download ONNX model: {e}")
            raise RuntimeError("Could not set up face detection model")
    
    def _setup_opencv_fallback(self, onnx_path: str):
        """Setup OpenCV DNN as fallback when OpenVINO model is not available"""
        print("[ULTRA LIGHT] Setting up OpenCV DNN fallback...")
        
        try:
            self.opencv_net = cv2.dnn.readNetFromONNX(onnx_path)
            self.opencv_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.opencv_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
            self.use_opencv_fallback = True
            print("[ULTRA LIGHT] OpenCV DNN fallback ready!")
            
            # Get output layer names
            output_layer_names = self.opencv_net.getUnconnectedOutLayersNames()
            print(f"[ULTRA LIGHT] OpenCV output layers: {output_layer_names}")
            
        except Exception as e:
            print(f"[ULTRA LIGHT ERROR] OpenCV fallback failed: {e}")
            raise
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for the model
        
        Args:
            image: Input image in BGR format
            
        Returns:
            Preprocessed image tensor
        """
        # Resize to model input size
        resized = cv2.resize(image, self.input_size)
        
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize pixel values
        normalized = rgb_image.astype(np.float32)
        normalized = (normalized - 127.0) / 128.0
        
        # Change data layout from HWC to CHW
        preprocessed = normalized.transpose(2, 0, 1)
        
        # Add batch dimension
        preprocessed = np.expand_dims(preprocessed, axis=0)
        
        return preprocessed
    
    def postprocess_outputs(self, boxes: np.ndarray, scores: np.ndarray, 
                          original_shape: Tuple[int, int]) -> List[Tuple[int, int, int, int, float]]:
        """
        Postprocess model outputs to get face bounding boxes
        
        Args:
            boxes: Raw box predictions
            scores: Raw score predictions
            original_shape: Original image shape (height, width)
            
        Returns:
            List of (x1, y1, x2, y2, confidence) tuples
        """
        # Get face scores (class 1, background is class 0)
        face_scores = scores[0, :, 1]
        
        # Filter by confidence threshold
        valid_indices = face_scores > self.confidence_threshold
        
        if not np.any(valid_indices):
            return []
        
        valid_boxes = boxes[0, valid_indices, :]
        valid_scores = face_scores[valid_indices]
        
        # Convert normalized coordinates to pixel coordinates
        orig_h, orig_w = original_shape
        
        # Boxes are in format [x_min, y_min, x_max, y_max] normalized
        x1 = (valid_boxes[:, 0] * orig_w).astype(int)
        y1 = (valid_boxes[:, 1] * orig_h).astype(int)
        x2 = (valid_boxes[:, 2] * orig_w).astype(int)
        y2 = (valid_boxes[:, 3] * orig_h).astype(int)
        
        # Ensure coordinates are within image bounds
        x1 = np.clip(x1, 0, orig_w - 1)
        y1 = np.clip(y1, 0, orig_h - 1)
        x2 = np.clip(x2, 0, orig_w - 1)
        y2 = np.clip(y2, 0, orig_h - 1)
        
        # Apply Non-Maximum Suppression
        boxes_for_nms = np.column_stack([x1, y1, x2 - x1, y2 - y1])  # Convert to (x, y, w, h)
        indices = cv2.dnn.NMSBoxes(
            boxes_for_nms.tolist(),
            valid_scores.tolist(),
            self.confidence_threshold,
            self.nms_threshold
        )
        
        # Extract final detections
        final_detections = []
        if len(indices) > 0:
            for i in indices.flatten():
                final_detections.append((
                    int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i]), float(valid_scores[i])
                ))
        
        return final_detections
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """
        Detect faces in an image
        
        Args:
            image: Input image in BGR format
            
        Returns:
            List of (x1, y1, x2, y2, confidence) tuples
        """
        if hasattr(self, 'use_opencv_fallback'):
            return self._detect_opencv_fallback(image)
        
        try:
            # Preprocess image
            input_tensor = self.preprocess_image(image)
            
            # Run inference
            results = self.compiled_model([input_tensor])
            
            # Get outputs
            boxes = results[self.output_layers['boxes']]
            scores = results[self.output_layers['scores']]
            
            # Postprocess
            detections = self.postprocess_outputs(boxes, scores, image.shape[:2])
            
            # Update FPS
            self._update_fps()
            
            return detections
            
        except Exception as e:
            print(f"[ULTRA LIGHT ERROR] Detection failed: {e}")
            return []
    
    def _detect_opencv_fallback(self, image: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """Fallback detection using OpenCV DNN"""
        try:
            # Preprocess for OpenCV DNN - note the input format for this model
            blob = cv2.dnn.blobFromImage(
                image, 
                scalefactor=1.0/128.0, 
                size=self.input_size,
                mean=(127.0, 127.0, 127.0),
                swapRB=True  # Convert BGR to RGB
            )
            
            # Set input and run forward pass
            self.opencv_net.setInput(blob)
            outputs = self.opencv_net.forward()
            
            # Process outputs - Ultra Lightweight Face Detection has specific output format
            detections = []
            
            if len(outputs) >= 2:
                # The model typically outputs boxes and scores
                scores_output = outputs[0]  # Shape: [1, N, 2] where N is number of anchors
                boxes_output = outputs[1]   # Shape: [1, N, 4] where N is number of anchors
                
                # Ensure we have the right shapes
                if len(scores_output.shape) == 3 and len(boxes_output.shape) == 3:
                    # Get face scores (class 1, background is class 0)
                    face_scores = scores_output[0, :, 1]
                    
                    # Filter by confidence threshold
                    valid_indices = face_scores > self.confidence_threshold
                    
                    if np.any(valid_indices):
                        valid_boxes = boxes_output[0, valid_indices, :]
                        valid_scores = face_scores[valid_indices]
                        
                        # Convert normalized coordinates to pixel coordinates
                        orig_h, orig_w = image.shape[:2]
                        
                        # Boxes are in format [x_min, y_min, x_max, y_max] normalized
                        x1 = (valid_boxes[:, 0] * orig_w).astype(int)
                        y1 = (valid_boxes[:, 1] * orig_h).astype(int)
                        x2 = (valid_boxes[:, 2] * orig_w).astype(int)
                        y2 = (valid_boxes[:, 3] * orig_h).astype(int)
                        
                        # Ensure coordinates are within image bounds
                        x1 = np.clip(x1, 0, orig_w - 1)
                        y1 = np.clip(y1, 0, orig_h - 1)
                        x2 = np.clip(x2, 0, orig_w - 1)
                        y2 = np.clip(y2, 0, orig_h - 1)
                        
                        # Apply Non-Maximum Suppression
                        boxes_for_nms = np.column_stack([x1, y1, x2 - x1, y2 - y1])
                        indices = cv2.dnn.NMSBoxes(
                            boxes_for_nms.tolist(),
                            valid_scores.tolist(),
                            self.confidence_threshold,
                            self.nms_threshold
                        )
                        
                        # Extract final detections
                        if len(indices) > 0:
                            for i in indices.flatten():
                                detections.append((
                                    int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i]), float(valid_scores[i])
                                ))
            
            self._update_fps()
            return detections
            
        except Exception as e:
            print(f"[ULTRA LIGHT ERROR] OpenCV fallback detection failed: {e}")
            return []
    
    def _update_fps(self):
        """Update FPS calculation"""
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if elapsed >= 1.0:  # Update every second
            self.last_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.start_time = current_time
    
    def get_fps(self) -> float:
        """Get current FPS"""
        return self.last_fps
    
    def draw_detections(self, image: np.ndarray, detections: List[Tuple[int, int, int, int, float]], 
                       color: Tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> np.ndarray:
        """
        Draw detection boxes on image
        
        Args:
            image: Input image
            detections: List of (x1, y1, x2, y2, confidence) tuples
            color: Box color (B, G, R)
            thickness: Box line thickness
            
        Returns:
            Image with drawn detections
        """
        result_image = image.copy()
        
        for x1, y1, x2, y2, confidence in detections:
            # Draw bounding box
            cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
            
            # Draw confidence score
            label = f"Face: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            
            # Background for text
            cv2.rectangle(result_image, 
                         (x1, y1 - label_size[1] - 5), 
                         (x1 + label_size[0], y1), 
                         color, -1)
            
            # Text
            cv2.putText(result_image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw FPS
        fps_text = f"FPS: {self.last_fps:.1f}"
        cv2.putText(result_image, fps_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return result_image


# Convenience function for easy integration
def create_ultra_light_detector(confidence_threshold: float = 0.7) -> UltraLightFaceDetector:
    """Create and return an UltraLightFaceDetector instance"""
    return UltraLightFaceDetector(confidence_threshold=confidence_threshold)


if __name__ == "__main__":
    # Test the detector
    print("Testing Ultra Light Face Detector...")
    
    try:
        detector = UltraLightFaceDetector()
        print("Detector created successfully!")
        
        # Test with webcam if available
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("Testing with webcam... Press 'q' to quit")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Detect faces
                detections = detector.detect_faces(frame)
                
                # Draw results
                result_frame = detector.draw_detections(frame, detections)
                
                # Show frame
                cv2.imshow("Ultra Light Face Detection", result_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cap.release()
            cv2.destroyAllWindows()
        else:
            print("No webcam available for testing")
            
    except Exception as e:
        print(f"Test failed: {e}")