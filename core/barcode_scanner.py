import cv2
import numpy as np
import re

# Try to import pyzbar for comprehensive barcode support
try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
    print("[BARCODE] pyzbar imported successfully - full barcode support enabled")
except ImportError:
    PYZBAR_AVAILABLE = False
    print("[BARCODE] pyzbar not available - QR code only support (install with: pip install pyzbar)")

class BarcodeScanner:
    def __init__(self):
        # Initialize QR code detector (OpenCV fallback)
        self.qr_detector = cv2.QRCodeDetector()
        
        # Define supported formats
        if PYZBAR_AVAILABLE:
            self.supported_formats = [
                "QR_CODE", "CODE128", "CODE39", "CODE93", 
                "EAN13", "EAN8", "UPC_A", "UPC_E", "CODABAR", 
                "ITF", "DATAMATRIX", "PDF417", "AZTEC"
            ]
        else:
            self.supported_formats = ["QR_CODE"]  # OpenCV only supports QR codes
        
        print(f"[BARCODE] Supported formats: {', '.join(self.supported_formats)}")
    
    def scan_frame(self, frame):
        """Scan a frame for QR codes and barcodes"""
        try:
            detected_codes = []
            
            # Convert to grayscale for better detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Method 1: Try pyzbar for comprehensive barcode detection (if available)
            if PYZBAR_AVAILABLE:
                try:
                    barcodes = pyzbar.decode(gray)
                    for barcode in barcodes:
                        # Extract barcode data
                        data = barcode.data.decode('utf-8')
                        barcode_type = barcode.type
                        
                        # Get barcode rectangle
                        rect = barcode.rect
                        points = np.array([
                            [rect.left, rect.top],
                            [rect.left + rect.width, rect.top],
                            [rect.left + rect.width, rect.top + rect.height],
                            [rect.left, rect.top + rect.height]
                        ])
                        
                        detected_codes.append({
                            'data': data,
                            'type': barcode_type,
                            'points': points,
                            'employee_id': self.extract_employee_id(data)
                        })
                        
                        print(f"[BARCODE] Detected {barcode_type}: {data}")
                        
                except Exception as e:
                    print(f"[BARCODE] pyzbar detection error: {e}")
            
            # Method 2: Try OpenCV QR code detector (fallback or additional detection)
            try:
                data, points, _ = self.qr_detector.detectAndDecode(gray)
                if data:
                    # Check if this QR code was already detected by pyzbar
                    already_detected = any(code['data'] == data and code['type'] == 'QRCODE' 
                                         for code in detected_codes)
                    
                    if not already_detected:
                        detected_codes.append({
                            'data': data,
                            'type': 'QR_CODE',
                            'points': points.astype(int) if points is not None else None,
                            'employee_id': self.extract_employee_id(data)
                        })
                        print(f"[BARCODE] Detected QR_CODE (OpenCV): {data}")
                        
            except Exception as e:
                print(f"[BARCODE] OpenCV QR detection error: {e}")
            
            return detected_codes
            
        except Exception as e:
            print(f"[BARCODE] Error scanning frame: {e}")
            return []
    
    def extract_employee_id(self, data):
        """Extract employee ID from QR code/barcode data"""
        # Clean the data
        data = data.strip()
        
        # Pattern 1: Direct employee ID (alphanumeric, 3-10 characters)
        if re.match(r'^[A-Za-z0-9]{3,10}$', data):
            return data.upper()  # Convert to uppercase for consistency
        
        # Pattern 2: Numeric only (for pure numeric employee IDs)
        if re.match(r'^\d{3,8}$', data):
            return data
        
        # Pattern 3: JSON-like format (e.g., {"employee_id": "ABC123"}) - Check this FIRST before prefix patterns
        json_match = re.search(r'"?employee_id"?\s*:\s*"?([A-Za-z0-9]{3,10})"?', data, re.IGNORECASE)
        if json_match:
            return json_match.group(1).upper()
        
        # Pattern 4: URL-like format (e.g., "attendance://employee/ABC123")
        url_match = re.search(r'attendance://(?:employee|staff)/([A-Za-z0-9]{3,10})', data, re.IGNORECASE)
        if url_match:
            return url_match.group(1).upper()
        
        # Pattern 5: Employee ID with prefix (e.g., "EMP:12345", "ID:ABC123") - Check this LAST to avoid conflicts
        emp_match = re.search(r'(?:EMP|ID|STAFF)[\s:]*([A-Za-z0-9]{3,10})', data, re.IGNORECASE)
        if emp_match:
            return emp_match.group(1).upper()
        
        # If no pattern matches, return None
        return None
    
    def validate_employee_id(self, barcode_data):
        """Validate if barcode data is a valid employee ID format"""
        return self.extract_employee_id(barcode_data)
    
    def draw_barcode_boxes(self, frame, detected_codes):
        """Draw bounding boxes around detected QR codes and barcodes"""
        for code in detected_codes:
            points = code.get('points')
            if points is not None and len(points) >= 4:
                # Draw polygon around barcode/QR code
                cv2.polylines(frame, [points.astype(int)], True, (0, 255, 0), 2)
                
                # Prepare display text
                barcode_type = code['type']
                data = code['data']
                employee_id = code.get('employee_id')
                
                # Create informative text
                if employee_id:
                    text = f"{barcode_type}: {employee_id} ✓"
                    text_color = (0, 255, 0)  # Green for valid employee ID
                else:
                    text = f"{barcode_type}: {data[:20]}..." if len(data) > 20 else f"{barcode_type}: {data}"
                    text_color = (0, 165, 255)  # Orange for unrecognized data
                
                # Position text above the barcode
                x, y = int(points[0][0]), int(points[0][1])
                
                # Add background rectangle for better text visibility
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(frame, (x, y - 30), (x + text_size[0], y - 5), (0, 0, 0), -1)
                
                # Add text
                cv2.putText(frame, text, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
        
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
    
    def get_scanner_info(self):
        """Get information about scanner capabilities"""
        info = {
            'pyzbar_available': PYZBAR_AVAILABLE,
            'supported_formats': self.supported_formats,
            'total_formats': len(self.supported_formats)
        }
        
        if PYZBAR_AVAILABLE:
            info['recommendation'] = "Full barcode support enabled with pyzbar"
        else:
            info['recommendation'] = "Limited to QR codes only. Install pyzbar for full barcode support: pip install pyzbar"
        
        return info
    
    @staticmethod
    def install_pyzbar_instructions():
        """Get instructions for installing pyzbar"""
        return {
            'windows': 'pip install pyzbar',
            'linux': 'sudo apt-get install libzbar0 && pip install pyzbar',
            'macos': 'brew install zbar && pip install pyzbar',
            'note': 'pyzbar requires zbar library to be installed on the system'
        }

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
