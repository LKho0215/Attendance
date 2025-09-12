# Modern Face Recognition Attendance System

A comprehensive attendance tracking system with advanced face recognition, barcode/QR code scanning, and MongoDB integration.

## 🌟 Features

### Core Functionality
- **Advanced Face Recognition**: DeepFace with MobileFaceNet for high-accuracy recognition
- **Barcode/QR Code Scanning**: Support for employee ID scanning
- **MongoDB Integration**: Robust database with location-based attendance
- **Manual Camera Control**: User-activated camera for privacy and control
- **Confidence Filtering**: Smart threshold system (0.5) with visual feedback

### User Interface
- **Modern GUI**: Clean, intuitive interface using CustomTkinter
- **Real-time Camera Preview**: Live video feed with face detection boxes
- **Color-coded Detection**: Green (recognized), Yellow (unknown), Orange (low confidence)
- **Confirmation Dialogs**: Prevent accidental clock-ins with user confirmation
- **Fullscreen Kiosk Mode**: Optimized for touchscreen/keyboard operation

### Attendance Management
- **Dual-mode Operation**: CLOCK (time tracking) and CHECK (presence verification)
- **Location-based Tracking**: Multiple location support with favorites
- **Late Clock-in Detection**: Automatic flagging of late arrivals
- **Clock-out Restrictions**: Prevents early departures
- **Excel Export**: Professional reports with date filtering

### Performance & Optimization
- **60 FPS Camera**: Smooth video preview with optimized frame processing
- **Background Processing**: Non-blocking face recognition with threading
- **CPU Monitoring**: Performance tracking and optimization
- **Memory Management**: Efficient garbage collection and resource handling

## 🔧 Installation

### Prerequisites
- Python 3.11+
- MongoDB (local or Atlas)
- Windows 10/11 (optimized for Windows)

### Setup Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/LKho0215/Attendance.git
   cd Attendance
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure MongoDB**:
   - Edit `mongo_config.py` with your MongoDB connection details
   - For local MongoDB: Update connection string
   - For MongoDB Atlas: Add your cluster connection string

4. **Run the Application**:
   ```bash
   python simple_kiosk.py
   ```

## 🚀 Quick Start

### First Time Setup
1. **Start the System**: Run `python simple_kiosk.py`
2. **Register Employees**: Press `F2` or click Register to add new employees
3. **Activate Camera**: Press `+` to turn on camera for face recognition
4. **Scan QR Codes**: Use `F3` or scan employee QR codes

### Daily Operation
1. **Employee Interaction**: Press `+` to activate camera
2. **Face Recognition**: System detects and recognizes faces automatically
3. **Confirmation**: Employee confirms attendance in dialog
4. **Completion**: Camera deactivates, attendance recorded

## 📁 Project Structure

```
Attendance/
├── simple_kiosk.py           # Main kiosk application
├── mongo_config.py           # MongoDB configuration
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
├── core/                    # Core business logic
│   ├── attendance.py        # Attendance management
│   ├── deepface_recognition.py # Face recognition system
│   ├── mongodb_manager.py   # Database operations
│   ├── mongo_location_manager.py # Location management
│   └── barcode_scanner.py   # QR/Barcode scanning
├── data/                    # Data storage
│   ├── database/           # SQLite backup
│   ├── faces/             # Face images (temporary)
│   └── temp/              # Temporary files
├── exports/               # Excel export files
├── dist/                  # Compiled executables
└── docs/                  # Documentation files
```

## 💾 Database Schema

### MongoDB Collections

#### employees
```javascript
{
  "_id": ObjectId,
  "employee_id": "EMP001",
  "name": "John Doe",
  "department": "Engineering",
  "face_vectors": [Array of face embeddings],
  "created_at": ISODate
}
```

#### attendance
```javascript
{
  "_id": ObjectId,
  "employee_id": "EMP001",
  "employee_name": "John Doe",
  "timestamp": ISODate,
  "method": "face|qr|barcode",
  "action": "CLOCK_IN|CLOCK_OUT|CHECK_IN",
  "location_name": "Main Office",
  "location_address": "123 Main St",
  "is_late": false,
  "confidence": 0.85
}
```

#### favorite_locations
```javascript
{
  "_id": ObjectId,
  "name": "Main Office",
  "address": "123 Main Street, City",
  "usage_count": 150,
  "last_used": ISODate
}
```

## 🎯 Usage Guide

### Keyboard Shortcuts
- `F1`: Toggle between CLOCK and CHECK mode
- `F2`: Open employee registration dialog
- `F3`: Manual QR/barcode scan mode
- `F4`: Export attendance to Excel
- `F5`: Refresh attendance history
- `+`: Activate camera for face recognition
- `Esc`: Close dialogs or exit

### Employee Registration
1. Press `F2` to open registration dialog
2. Enter employee details (ID, name, department)
3. Take 8 diverse face photos for training
4. System creates face vectors automatically
5. Employee ready for recognition

### Attendance Workflow
1. **Camera Activation**: Employee presses `+`
2. **Face Detection**: Orange box shows face detected
3. **Recognition**: Green box shows recognized employee
4. **Confirmation**: Dialog asks for confirmation
5. **Recording**: Attendance saved to database
6. **Completion**: Camera deactivates automatically

### Location Management
- System remembers frequently used locations
- Favorite locations appear first in dropdown
- Manual location entry supported
- Location history tracked for reporting

## 📊 Features in Detail

### Face Recognition System
- **Model**: DeepFace with MobileFaceNet (lightweight, fast)
- **Detection**: Haar Cascades for face detection
- **Recognition**: Vector similarity matching
- **Threshold**: 0.5 minimum confidence with visual feedback
- **Performance**: 60 FPS camera with background processing

### Attendance Modes
- **CLOCK Mode**: Traditional time tracking with IN/OUT
- **CHECK Mode**: Presence verification without time tracking
- **Dual Support**: Switch between modes as needed

### Security Features
- **Confidence Thresholds**: Prevents false positives
- **Confirmation Dialogs**: User verification required
- **Manual Camera**: Privacy-focused, user-controlled activation
- **Audit Trail**: Complete attendance history with timestamps

## 🔧 Configuration

### Camera Settings
```python
# In core/deepface_recognition.py
CONFIDENCE_THRESHOLD = 0.5  # Minimum recognition confidence
FPS_TARGET = 60            # Camera frame rate
FRAME_SKIP = 5             # Process every 5th frame
```

### MongoDB Settings
```python
# In mongo_config.py
MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "attendance_system"
```

## 📈 Performance Optimization

### Camera Performance
- 60 FPS video preview
- Background face processing
- Frame skipping for efficiency
- Buffer size optimization

### Memory Management
- Automatic garbage collection
- Resource cleanup on errors
- Efficient face vector storage

### CPU Monitoring
- Real-time CPU usage tracking
- Performance logging
- Bottleneck identification

## 🚨 Troubleshooting

### Common Issues

**Camera Not Working**
- Check if camera is in use by another application
- Verify camera permissions
- Try different camera index in settings

**Face Recognition Poor**
- Ensure good lighting conditions
- Position face clearly in camera view
- Re-register employee with better photos

**MongoDB Connection**
- Verify MongoDB service is running
- Check connection string in `mongo_config.py`
- Ensure network connectivity for Atlas

**Performance Issues**
- Close unnecessary applications
- Check CPU usage in logs
- Consider reducing frame rate

## 🔄 Updates & Maintenance

### Regular Maintenance
- Monitor database size and performance
- Clean up temporary files periodically
- Update face vectors for improved accuracy
- Export attendance data for backup

### System Updates
- Keep Python dependencies updated
- Monitor MongoDB performance
- Review and adjust confidence thresholds
- Update documentation as needed

## 📄 License

This project is proprietary software. All rights reserved.

## 🤝 Support

For technical support or feature requests, please contact the development team.

---

**Built with ❤️ using Python, OpenCV, DeepFace, MongoDB, and CustomTkinter**
