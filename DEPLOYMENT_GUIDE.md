# Attendance System - Executable Deployment Guide

## Overview

This guide explains how to create and deploy standalone executable (.exe) files for the Attendance System. The executables can run on any Windows machine without requiring Python to be installed.

## Available Executables

### 1. SimpleKiosk.exe
- **Features**: Face recognition + QR/Barcode scanning + Manual entry
- **Requirements**: Webcam/camera required for face recognition
- **Use Case**: Full-featured kiosk with multiple attendance methods
- **File Size**: ~150-200 MB (includes OpenCV and face recognition libraries)

### 2. ScannerKiosk.exe  
- **Features**: QR/Barcode scanning + Manual entry (no camera/face recognition)
- **Requirements**: QR/Barcode scanner input device
- **Use Case**: Scanner-only kiosks, smaller file size, faster startup
- **File Size**: ~50-80 MB (lighter without OpenCV camera features)

## Building Executables

### Method 1: Build All (Recommended)
```batch
# Run this to build both executables at once
build_all.bat
```

### Method 2: Build Individual Executables
```batch
# Build Simple Kiosk only
build_simple_kiosk.bat

# Build Scanner Kiosk only  
build_scanner_kiosk.bat
```

### Method 3: Python Script (Advanced)
```batch
python build_executables.py
```

## What Gets Built

After successful build, you'll find in the `dist/` folder:

### Executable Files
- `SimpleKiosk.exe` - Face recognition + QR scanner kiosk
- `ScannerKiosk.exe` - QR/Barcode scanner only kiosk

### Launcher Scripts
- `Start_Simple_Kiosk.bat` - Easy launcher for Simple Kiosk
- `Start_Scanner_Kiosk.bat` - Easy launcher for Scanner Kiosk

### Supporting Files
- `data/` folder with database and face images
- `assets/` folder with icons and images
- `README.md`, `requirements.txt` for reference

## Deployment Instructions

### Step 1: Copy Files to Target Machine
1. Copy the entire `dist/` folder to your target kiosk machine
2. No Python installation required on the target machine
3. Ensure the folder structure remains intact

### Step 2: Hardware Setup

#### For SimpleKiosk.exe:
- Connect a webcam/camera (USB or built-in)
- Optionally connect a QR/Barcode scanner
- Test camera functionality

#### For ScannerKiosk.exe:
- Connect a QR/Barcode scanner (USB HID device)
- Configure scanner to send Enter after each scan
- No camera required

### Step 3: Run the Application

#### Easy Method (Recommended):
- Double-click `Start_Simple_Kiosk.bat` or `Start_Scanner_Kiosk.bat`
- The launcher will show system info and wait for confirmation

#### Direct Method:
- Double-click `SimpleKiosk.exe` or `ScannerKiosk.exe` directly
- Application starts immediately in fullscreen kiosk mode

## Kiosk Mode Controls

### Keyboard Shortcuts (Both Applications):
- **Numpad -** or **- key**: Exit with confirmation
- **Enter** or **Numpad Enter**: Manual employee ID entry
- **F1**: Show help
- **F4**: Toggle fullscreen mode (for debugging)
- **ESC**: Clear status messages

### Exit Confirmation:
1. Press **-** (minus) key to request exit
2. Confirmation overlay appears
3. Press **-** again to confirm exit, or **Enter** to cancel
4. Auto-cancels after 5 seconds if no input

## System Requirements

### Target Machine Requirements:
- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB free space
- **Display**: 1920x1080 recommended for optimal kiosk display

### Hardware Requirements:

#### SimpleKiosk.exe:
- USB webcam or built-in camera
- Optional: USB QR/Barcode scanner
- Keyboard/numpad for manual entry

#### ScannerKiosk.exe:
- USB QR/Barcode scanner (HID mode)
- Keyboard/numpad for manual entry
- No camera required

## Database and Data Management

### Database Location:
- `dist/data/database/attendance.db`
- SQLite database, automatically created if missing
- Contains employee records and attendance history

### Face Recognition Data:
- `dist/data/faces/` folder
- Contains face images for recognition
- Only used by SimpleKiosk.exe

### Backup Recommendations:
- Regularly backup the entire `data/` folder
- Database contains all attendance records
- Face images are needed for recognition functionality

## Troubleshooting

### Common Build Issues:

#### "Python not found" Error:
- Ensure Python 3.11+ is installed and in PATH
- Try running from Anaconda Prompt if using Anaconda

#### "PyInstaller not found" Error:
- Install PyInstaller: `pip install pyinstaller`
- The build scripts will auto-install if missing

#### Large File Sizes:
- This is normal for standalone executables
- SimpleKiosk.exe includes OpenCV (~100MB+ of libraries)
- ScannerKiosk.exe is smaller without camera libraries

### Common Runtime Issues:

#### Application Won't Start:
- Check Windows Defender/antivirus (may flag new executables)
- Ensure all files in `dist/` folder are present
- Try running from command prompt to see error messages

#### Camera Not Working (SimpleKiosk):
- Verify camera is connected and working in other applications
- Check Windows privacy settings for camera access
- Try different USB ports for webcam

#### Scanner Not Working:
- Ensure scanner is configured as HID keyboard device
- Test scanner in notepad (should type scanned data)
- Configure scanner to send Enter/Tab after each scan

#### Database Errors:
- Check that `data/database/` folder exists and is writable
- Verify no other application is using the database file
- Delete and recreate database if corrupted (will lose data)

## Security Considerations

### Kiosk Environment:
- Applications run in fullscreen mode to prevent user access to Windows
- Exit requires confirmation to prevent accidental closure
- No direct file system access provided to users

### Data Protection:
- Database files contain employee information
- Face images stored locally for recognition
- Consider encryption for sensitive deployments
- Regular backups recommended

## Performance Optimization

### SimpleKiosk.exe:
- Face recognition processing is CPU-intensive
- Recommended: Dedicated graphics card for better performance
- Consider faster CPU for multiple face recognition

### ScannerKiosk.exe:
- Lightweight operation, suitable for basic hardware
- Fast startup and low resource usage
- Suitable for older computers

## Network and Connectivity

### Offline Operation:
- Both applications work completely offline
- No internet connection required
- All data stored locally

### Network Database (Future):
- Current version uses local SQLite database
- Network database integration possible with custom modifications
- Contact developer for multi-kiosk network deployment

## Customization Options

### Visual Customization:
- Modify source code before building for custom branding
- Change colors, logos, text in Python source files
- Rebuild executables after modifications

### Functional Customization:
- Add custom fields to database
- Modify attendance logic
- Add new input methods or integrations

## Support and Maintenance

### Updating the Application:
1. Modify Python source code as needed
2. Run build process again to create new executables
3. Replace old executables with new ones
4. Database and settings are preserved

### Log Files:
- Applications print debug information to console
- For production, redirect output to log files if needed
- Monitor for error messages during operation

---

## Quick Start Checklist

- [ ] Run `build_all.bat` to create executables
- [ ] Copy `dist/` folder to target machine
- [ ] Connect camera (for SimpleKiosk) or scanner (for ScannerKiosk)
- [ ] Test hardware functionality
- [ ] Run launcher script or executable directly
- [ ] Test attendance recording with known employee
- [ ] Configure exit procedures for kiosk operators

---

*For technical support or custom modifications, refer to the source code documentation or contact the development team.*
