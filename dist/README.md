# Modern Attendance System

A comprehensive attendance tracking system with face recognition and barcode/QR code scanning capabilities.

## Features

- **Face Recognition**: OpenCV-powered face detection and recognition  
- **Barcode/QR Code Scanning**: Support for employee ID scanning
- **Modern GUI**: Clean, intuitive interface using CustomTkinter
- **Database Management**: SQLite-based employee and attendance tracking
- **Real-time Camera**: Live video feed for face recognition
- **Attendance Reports**: View daily and historical attendance data

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create Sample Data** (optional):
   ```bash
   python sample_data.py
   ```

3. **Run the Application**:
   ```bash
   python main.py
   ```

4. **Run in Kiosk Mode** (for touchscreen/keyboard-only setups):
   ```bash
   python simple_kiosk.py
   ```
- **Real-time Updates**: Live attendance tracking and reporting

## Requirements

- Python 3.8+
- OpenCV
- customtkinter
- PIL (Pillow)
- pyzbar (for barcode/QR scanning)
- sqlite3 (built-in)
- face-recognition

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

## Project Structure

```
attendance-system/
├── main.py                 # Full GUI application
├── simple_kiosk.py        # Kiosk mode (recommended for your setup)
├── requirements.txt        # Python dependencies
├── sample_data.py         # Sample data generator
├── verify_system.py       # System verification script
├── README.md              # Documentation
├── core/                  # Core business logic
│   ├── __init__.py
│   ├── attendance.py      # Attendance management
│   ├── barcode_scanner.py # Barcode/QR scanning
│   ├── database.py        # Database operations
│   └── face_recognition.py # Face recognition system
├── gui/                   # Full GUI interface
│   ├── __init__.py
│   └── main_window.py     # Main GUI window
├── data/                  # Data storage
│   ├── database/          # SQLite database files
│   ├── faces/            # Face image storage
│   └── temp/             # Temporary files
└── assets/               # UI assets
    ├── icons/
    └── images/
```

## Usage

1. **Employee Management**: Add new employees with their photos and employee IDs
2. **Face Recognition**: Click on "Face Recognition" to start facial attendance
3. **Barcode/QR Scanning**: Use "Scan Code" for barcode/QR code attendance
4. **View Records**: Check attendance history and generate reports

## Database Schema

### Employees Table
- id (PRIMARY KEY)
- employee_id (UNIQUE)
- name
- department
- face_encoding (for face recognition)
- created_at

### Attendance Table
- id (PRIMARY KEY)
- employee_id (FOREIGN KEY)
- timestamp
- method (face/barcode/qr)
- status (in/out)
