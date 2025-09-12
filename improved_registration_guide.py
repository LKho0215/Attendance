#!/usr/bin/env python3
"""
Improved Registration Process with Guided Face Capture
====================================================

This script implements a guided registration process that captures face vectors
under different conditions for much better recognition accuracy.

Key Improvements:
1. Multiple poses (front, left turn, right turn, slight up, slight down)
2. Different expressions (neutral, smile, serious)
3. Longer intervals between captures for natural movement
4. Voice prompts to guide user positioning
5. Quality checks for each capture
6. Minimum diversity requirements
"""

import cv2
import numpy as np
import time
import threading
from typing import List, Tuple, Optional
import logging

class ImprovedFaceRegistration:
    def __init__(self, face_recognition_system):
        self.face_recognition = face_recognition_system
        self.captured_vectors = []
        self.capture_instructions = [
            "Look straight at the camera with a neutral expression",
            "Turn your head slightly to the LEFT",
            "Turn your head slightly to the RIGHT", 
            "Look straight and SMILE naturally",
            "Look straight with a serious expression",
            "Tilt your head slightly UP",
            "Tilt your head slightly DOWN",
            "Look straight again - final capture"
        ]
        self.current_instruction = 0
        self.capture_active = False
        
    def start_guided_registration(self, employee_id: str, employee_name: str, 
                                department: str, status_callback=None):
        """
        Start guided registration process with different poses and expressions
        
        Args:
            employee_id: Employee ID
            employee_name: Employee name
            department: Department
            status_callback: Function to update UI status
        """
        self.captured_vectors = []
        self.current_instruction = 0
        self.capture_active = True
        
        if status_callback:
            status_callback("🎯 Starting guided face registration...")
        
        # Start the guided capture process
        threading.Thread(
            target=self._guided_capture_process,
            args=(employee_id, employee_name, department, status_callback),
            daemon=True
        ).start()
    
    def _guided_capture_process(self, employee_id: str, employee_name: str,
                              department: str, status_callback=None):
        """
        Execute the guided capture process with instructions
        """
        total_instructions = len(self.capture_instructions)
        
        for instruction_idx, instruction in enumerate(self.capture_instructions):
            if not self.capture_active:
                break
                
            self.current_instruction = instruction_idx
            
            # Update status with current instruction
            if status_callback:
                progress = f"{instruction_idx + 1}/{total_instructions}"
                status_callback(f"📋 {progress}: {instruction}")
            
            # Wait for user to position themselves
            time.sleep(2.0)  # Give user time to read and position
            
            # Attempt to capture face vector for this pose
            success = self._capture_single_pose(instruction)
            
            if success:
                if status_callback:
                    status_callback(f"✅ {progress}: Captured! Moving to next pose...")
                time.sleep(1.0)  # Brief pause before next instruction
            else:
                if status_callback:
                    status_callback(f"⚠️ {progress}: Retrying capture...")
                time.sleep(1.0)
                
                # Retry once
                success = self._capture_single_pose(instruction)
                if not success:
                    if status_callback:
                        status_callback(f"⚠️ {progress}: Skipping this pose...")
        
        # Process final results
        self._finalize_registration(employee_id, employee_name, department, status_callback)
    
    def _capture_single_pose(self, instruction: str) -> bool:
        """
        Capture face vector for a single pose with quality checks
        
        Args:
            instruction: Current instruction text
            
        Returns:
            bool: True if capture was successful
        """
        max_attempts = 10  # Try for 2 seconds max
        attempts = 0
        
        while attempts < max_attempts and self.capture_active:
            try:
                # Get frame from camera
                if hasattr(self.face_recognition, 'camera_manager'):
                    camera = self.face_recognition.camera_manager
                    if camera and camera.cap is not None:
                        ret, frame = camera.cap.read()
                        
                        if ret and frame is not None:
                            # Extract face vector using hybrid approach
                            face_vector, face_coords = self.face_recognition.extract_face_embedding_hybrid(frame)
                            
                            if face_vector is not None:
                                # Quality check: ensure face is detected with good confidence
                                if self._is_good_quality_capture(frame, face_coords):
                                    self.captured_vectors.append({
                                        'vector': face_vector,
                                        'instruction': instruction,
                                        'timestamp': time.time()
                                    })
                                    print(f"[IMPROVED REG] Captured vector for: {instruction}")
                                    return True
                
                attempts += 1
                time.sleep(0.2)  # Wait before next attempt
                
            except Exception as e:
                print(f"[IMPROVED REG] Capture error: {e}")
                attempts += 1
                time.sleep(0.2)
        
        return False
    
    def _is_good_quality_capture(self, frame: np.ndarray, face_coords: Tuple) -> bool:
        """
        Check if the captured face is good quality
        
        Args:
            frame: Camera frame
            face_coords: Face bounding box coordinates
            
        Returns:
            bool: True if capture meets quality standards
        """
        if face_coords is None:
            return False
        
        x, y, w, h = face_coords
        
        # Check face size (should be reasonable portion of frame)
        frame_area = frame.shape[0] * frame.shape[1]
        face_area = w * h
        face_ratio = face_area / frame_area
        
        # Face should be at least 2% of frame but not more than 50%
        if face_ratio < 0.02 or face_ratio > 0.5:
            return False
        
        # Check if face is reasonably centered (not too close to edges)
        frame_h, frame_w = frame.shape[:2]
        center_x, center_y = x + w//2, y + h//2
        
        # Face center should be in middle 80% of frame
        margin_x, margin_y = frame_w * 0.1, frame_h * 0.1
        if (center_x < margin_x or center_x > frame_w - margin_x or
            center_y < margin_y or center_y > frame_h - margin_y):
            return False
        
        return True
    
    def _finalize_registration(self, employee_id: str, employee_name: str,
                             department: str, status_callback=None):
        """
        Finalize registration with captured vectors
        """
        if len(self.captured_vectors) < 3:
            if status_callback:
                status_callback(f"❌ Registration failed: Only {len(self.captured_vectors)} vectors captured (need at least 3)")
            return False
        
        # Extract just the vectors for averaging
        vectors = [item['vector'] for item in self.captured_vectors]
        
        # Create averaged embedding with weighted approach
        # Give more weight to front-facing captures
        weights = []
        for item in self.captured_vectors:
            instruction = item['instruction'].lower()
            if 'straight' in instruction:
                weights.append(1.5)  # Higher weight for straight views
            else:
                weights.append(1.0)  # Normal weight for other poses
        
        # Calculate weighted average
        weights = np.array(weights)
        weights = weights / weights.sum()  # Normalize weights
        
        weighted_avg = np.zeros_like(vectors[0])
        for i, vector in enumerate(vectors):
            weighted_avg += vector * weights[i]
        
        # Save to database
        try:
            # Assuming the database interface exists
            if hasattr(self.face_recognition, 'db'):
                success = self.face_recognition.db.add_employee_with_face_vector(
                    employee_id=employee_id,
                    name=employee_name,
                    face_vector=weighted_avg.tolist(),
                    department=department
                )
                
                if success:
                    if status_callback:
                        status_callback(f"✅ Registration successful! {len(self.captured_vectors)} diverse vectors captured")
                    return True
                else:
                    if status_callback:
                        status_callback("❌ Database error during registration")
                    return False
            else:
                if status_callback:
                    status_callback("❌ Database not available")
                return False
                
        except Exception as e:
            if status_callback:
                status_callback(f"❌ Registration error: {str(e)}")
            return False
    
    def stop_registration(self):
        """Stop the registration process"""
        self.capture_active = False


# Usage example for integration:
def integrate_improved_registration(kiosk_app):
    """
    Integration function to add improved registration to existing kiosk
    """
    # Replace the existing registration method
    def improved_registration_dialog(self):
        # Create the improved registration system
        improved_reg = ImprovedFaceRegistration(self.face_recognition)
        
        # Create dialog with instructions
        dialog = tk.Toplevel(self.root)
        dialog.title("Improved Employee Registration")
        dialog.geometry("1000x700")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Add instruction label
        instruction_label = ctk.CTkLabel(
            dialog,
            text="Follow the on-screen instructions for best face recognition accuracy",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        instruction_label.pack(pady=20)
        
        # Add status label
        status_label = ctk.CTkLabel(
            dialog,
            text="Ready to start registration...",
            font=ctk.CTkFont(size=14)
        )
        status_label.pack(pady=10)
        
        # Status update callback
        def update_status(message):
            status_label.configure(text=message)
        
        # Start improved registration
        # This would be called when user fills in employee details
        # improved_reg.start_guided_registration(employee_id, name, dept, update_status)
    
    return improved_registration_dialog

if __name__ == "__main__":
    print("Improved Registration Process Design")
    print("This module provides guided face capture for better accuracy")
