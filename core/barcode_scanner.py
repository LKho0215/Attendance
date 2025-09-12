import cv2
import numpy as np
import re

class BarcodeScanner:
    def __init__(self):
        # Initialize QR code detector
        self.qr_detector = cv2.QRCodeDetector()
        self.supported_formats = ["QR_CODE"]  # We'll focus on QR codes with OpenCV
    
    def scan_frame(self, frame):
        """Scan a frame for QR codes using OpenCV"""
        try:
            # Convert to grayscale for better detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect and decode QR codes
            data, points, _ = self.qr_detector.detectAndDecode(gray)
            
            detected_codes = []
            if data:
                # QR code detected
                detected_codes.append({
                    'data': data,
                    'type': 'QR_CODE',
                    'points': points.astype(int) if points is not None else None,
                    'employee_id': self.extract_employee_id(data)
                })
            
            return detected_codes
            
        except Exception as e:
            print(f"Error scanning frame: {e}")
            return []
    
    def extract_employee_id(self, data):
        """Extract employee ID from QR code data"""
        # Clean the data
        data = data.strip()
        
        # Check if it's a valid employee ID format
        # Assuming employee IDs are alphanumeric and 3-10 characters
        if re.match(r'^[A-Za-z0-9]{3,10}$', data):
            return data.upper()  # Convert to uppercase for consistency
        
        return None
    
    def validate_employee_id(self, barcode_data):
        """Validate if barcode data is a valid employee ID format"""
        return self.extract_employee_id(barcode_data)
    
    def draw_barcode_boxes(self, frame, detected_codes):
        """Draw bounding boxes around detected QR codes"""
        for code in detected_codes:
            points = code.get('points')
            if points is not None and len(points) == 4:
                # Draw polygon around QR code
                cv2.polylines(frame, [points], True, (0, 255, 0), 2)
                
                # Add text
                text = f"{code['type']}: {code['data']}"
                x, y = points[0][0], points[0][1]
                cv2.putText(frame, text, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return frame
    
    def process_video_frame(self, frame):
        """Process a video frame and return detected employee IDs"""
        detected_codes = self.scan_frame(frame)
        valid_employee_ids = []
        
        for code in detected_codes:
            employee_id = code.get('employee_id')
            if employee_id:
                valid_employee_ids.append({
                    'employee_id': employee_id,
                    'type': code['type'],
                    'points': code.get('points')
                })
        
        return valid_employee_ids, detected_codes

class QRCodeGenerator:
    """Generate QR codes for employee IDs using OpenCV"""
    
    @staticmethod
    def generate_qr_code_opencv(employee_id):
        """Generate QR code data for an employee ID that can be displayed"""
        # This is a simple text representation
        # For actual QR code generation, you'd need the qrcode library
        return f"Employee ID: {employee_id}"
    
    @staticmethod
    def generate_qr_code(employee_id, save_path=None):
        """Generate QR code for an employee ID (requires qrcode library)"""
        try:
            import qrcode
            from PIL import Image
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(employee_id)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            if save_path:
                img.save(save_path)
            
            return img
        except ImportError:
            print("qrcode library not installed. For QR code generation, install with: pip install qrcode[pil]")
            return None
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return None
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return None
