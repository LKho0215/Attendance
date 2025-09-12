#!/usr/bin/env python3
"""
Build script to create standalone executables for the Attendance System
Uses PyInstaller to create Windows .exe files
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def run_command(command_list, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"COMMAND: {' '.join(command_list)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command_list, check=True, capture_output=True, text=True)
        print("✓ SUCCESS")
        if result.stdout:
            print("STDOUT:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ ERROR: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def clean_previous_builds():
    """Clean up previous build artifacts"""
    print("\n" + "="*60)
    print("CLEANING PREVIOUS BUILD ARTIFACTS")
    print("="*60)
    
    # Directories to clean
    dirs_to_clean = ['build', 'dist']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}/ directory...")
            shutil.rmtree(dir_name)
            print(f"✓ Removed {dir_name}/")
        else:
            print(f"• {dir_name}/ directory not found (nothing to clean)")
    
    # Spec files to clean
    spec_files = ['simple_kiosk.spec', 'scanner_kiosk.spec']
    for spec_file in spec_files:
        if os.path.exists(spec_file):
            print(f"Removing {spec_file}...")
            os.remove(spec_file)
            print(f"✓ Removed {spec_file}")
        else:
            print(f"• {spec_file} not found (nothing to clean)")

def build_simple_kiosk():
    """Build simple_kiosk.py into executable"""
    print("\n" + "="*60)
    print("BUILDING SIMPLE KIOSK (Face Recognition + QR Scanner)")
    print("="*60)
    
    # PyInstaller command for simple_kiosk
    command = [
        "python", "-m", "PyInstaller",
        "--onefile",                    # Create single executable
        "--windowed",                   # Hide console window
        "--name=SimpleKiosk",           # Output filename
        "--icon=assets/icons/attendance.ico" if os.path.exists("assets/icons/attendance.ico") else "",
        "--add-data=data;data",         # Include data directory
        "--add-data=assets;assets",     # Include assets directory
        "--add-data=core;core",         # Include core modules
        "--hidden-import=cv2",          # Ensure OpenCV is included
        "--hidden-import=PIL",          # Ensure Pillow is included
        "--hidden-import=customtkinter", # Ensure CustomTkinter is included
        "--hidden-import=numpy",        # Ensure NumPy is included
        "--hidden-import=pyzbar",       # Ensure pyzbar is included
        "--hidden-import=tkinter",      # Ensure tkinter is included
        "--collect-all=customtkinter",  # Collect all CustomTkinter files
        "--collect-all=cv2",            # Collect all OpenCV files
        "simple_kiosk.py"
    ]
    
    # Filter out empty icon parameter
    command = [arg for arg in command if arg]
    
    return run_command(command, "Building Simple Kiosk Executable")

def build_scanner_kiosk():
    """Build scanner_kiosk.py into executable"""
    print("\n" + "="*60)
    print("BUILDING SCANNER KIOSK (QR/Barcode Scanner Only)")
    print("="*60)
    
    # PyInstaller command for scanner_kiosk
    command = [
        "python", "-m", "PyInstaller",
        "--onefile",                    # Create single executable
        "--windowed",                   # Hide console window
        "--name=ScannerKiosk",          # Output filename
        "--icon=assets/icons/attendance.ico" if os.path.exists("assets/icons/attendance.ico") else "",
        "--add-data=data;data",         # Include data directory
        "--add-data=assets;assets",     # Include assets directory
        "--add-data=core;core",         # Include core modules
        "--hidden-import=PIL",          # Ensure Pillow is included
        "--hidden-import=customtkinter", # Ensure CustomTkinter is included
        "--hidden-import=numpy",        # Ensure NumPy is included
        "--hidden-import=tkinter",      # Ensure tkinter is included
        "--collect-all=customtkinter",  # Collect all CustomTkinter files
        "scanner_kiosk.py"
    ]
    
    # Filter out empty icon parameter
    command = [arg for arg in command if arg]
    
    return run_command(command, "Building Scanner Kiosk Executable")

def copy_required_files():
    """Copy required files to dist directory"""
    print("\n" + "="*60)
    print("COPYING REQUIRED FILES TO DIST DIRECTORY")
    print("="*60)
    
    # Create directories if they don't exist
    os.makedirs("dist/data/database", exist_ok=True)
    os.makedirs("dist/data/faces", exist_ok=True)
    os.makedirs("dist/data/temp", exist_ok=True)
    
    # Copy database if it exists
    if os.path.exists("data/database/attendance.db"):
        shutil.copy2("data/database/attendance.db", "dist/data/database/")
        print("✓ Copied attendance.db database")
    else:
        print("• Database file not found - will be created on first run")
    
    # Copy face images if they exist
    if os.path.exists("data/faces") and os.listdir("data/faces"):
        for face_file in os.listdir("data/faces"):
            if face_file.endswith(('.jpg', '.png', '.jpeg')):
                shutil.copy2(f"data/faces/{face_file}", "dist/data/faces/")
        print("✓ Copied face recognition images")
    else:
        print("• No face images found - add them to data/faces/ for face recognition")
    
    # Copy assets if they exist
    if os.path.exists("assets"):
        if os.path.exists("dist/assets"):
            shutil.rmtree("dist/assets")
        shutil.copytree("assets", "dist/assets")
        print("✓ Copied assets directory")
    else:
        print("• No assets directory found")
    
    # Copy documentation
    docs_to_copy = ["README.md", "DEPLOYMENT_GUIDE.md", "requirements.txt"]
    for doc in docs_to_copy:
        if os.path.exists(doc):
            shutil.copy2(doc, "dist/")
            print(f"✓ Copied {doc}")

def create_launcher_scripts():
    """Create convenient launcher scripts"""
    print("\n" + "="*60)
    print("CREATING LAUNCHER SCRIPTS")
    print("="*60)
    
    # Simple Kiosk launcher
    simple_launcher = """@echo off
title Simple Kiosk - Face Recognition + QR Scanner
echo Starting Simple Kiosk (Face Recognition + QR Scanner)...
echo.
echo This kiosk supports:
echo - Face recognition via camera
echo - QR code / barcode scanning
echo - Manual employee ID entry
echo.
echo Press any key to start, or close this window to cancel
pause > nul
echo.
echo Starting application...
SimpleKiosk.exe
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
    echo Press any key to close...
    pause > nul
)
"""
    
    # Scanner Kiosk launcher
    scanner_launcher = """@echo off
title Scanner Kiosk - QR/Barcode Scanner Only
echo Starting Scanner Kiosk (QR/Barcode Scanner Only)...
echo.
echo This kiosk supports:
echo - QR code / barcode scanning via input device
echo - Manual employee ID entry
echo - Optimized for scanner-only environments
echo.
echo Press any key to start, or close this window to cancel
pause > nul
echo.
echo Starting application...
ScannerKiosk.exe
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
    echo Press any key to close...
    pause > nul
)
"""
    
    # Write launcher scripts
    with open("dist/Start_Simple_Kiosk.bat", "w") as f:
        f.write(simple_launcher)
    print("✓ Created Start_Simple_Kiosk.bat")
    
    with open("dist/Start_Scanner_Kiosk.bat", "w") as f:
        f.write(scanner_launcher)
    print("✓ Created Start_Scanner_Kiosk.bat")

def show_build_summary():
    """Show build summary and instructions"""
    print("\n" + "="*60)
    print("BUILD COMPLETE - SUMMARY")
    print("="*60)
    
    dist_path = os.path.abspath("dist")
    
    print(f"\n📁 EXECUTABLE FILES LOCATION: {dist_path}")
    print("\n🚀 CREATED EXECUTABLES:")
    
    if os.path.exists("dist/SimpleKiosk.exe"):
        size = os.path.getsize("dist/SimpleKiosk.exe") / (1024*1024)
        print(f"  ✓ SimpleKiosk.exe ({size:.1f} MB)")
        print("    - Face Recognition + QR/Barcode Scanner")
        print("    - Requires camera for face recognition")
    
    if os.path.exists("dist/ScannerKiosk.exe"):
        size = os.path.getsize("dist/ScannerKiosk.exe") / (1024*1024)
        print(f"  ✓ ScannerKiosk.exe ({size:.1f} MB)")
        print("    - QR/Barcode Scanner Only (no camera required)")
        print("    - Optimized for scanner-only kiosks")
    
    print("\n🎯 LAUNCHER SCRIPTS:")
    if os.path.exists("dist/Start_Simple_Kiosk.bat"):
        print("  ✓ Start_Simple_Kiosk.bat - Easy launcher for Simple Kiosk")
    if os.path.exists("dist/Start_Scanner_Kiosk.bat"):
        print("  ✓ Start_Scanner_Kiosk.bat - Easy launcher for Scanner Kiosk")
    
    print("\n📋 DEPLOYMENT INSTRUCTIONS:")
    print("  1. Copy the entire 'dist' folder to your target machine")
    print("  2. Run the .bat launcher files for easy startup")
    print("  3. Or run the .exe files directly")
    print("  4. Database and face images are included automatically")
    
    print("\n⚙️  SYSTEM REQUIREMENTS:")
    print("  - Windows 10/11 (64-bit)")
    print("  - For SimpleKiosk: Camera/webcam required")
    print("  - For ScannerKiosk: QR/Barcode scanner required")
    print("  - No Python installation needed on target machine")
    
    print("\n" + "="*60)
    print("BUILD PROCESS COMPLETE!")
    print("="*60)

def main():
    """Main build process"""
    print("ATTENDANCE SYSTEM - EXECUTABLE BUILDER")
    print("Building standalone Windows executables...")
    
    # Check if we're in the right directory
    if not os.path.exists("simple_kiosk.py") and not os.path.exists("scanner_kiosk.py"):
        print("❌ ERROR: Python source files not found!")
        print("Please run this script from the Attendance project directory.")
        sys.exit(1)
    
    # Clean previous builds
    clean_previous_builds()
    
    # Track build success
    simple_success = False
    scanner_success = False
    
    # Build executables
    if os.path.exists("simple_kiosk.py"):
        simple_success = build_simple_kiosk()
    else:
        print("⚠️  simple_kiosk.py not found - skipping")
    
    if os.path.exists("scanner_kiosk.py"):
        scanner_success = build_scanner_kiosk()
    else:
        print("⚠️  scanner_kiosk.py not found - skipping")
    
    # Copy required files and create launchers
    if simple_success or scanner_success:
        copy_required_files()
        create_launcher_scripts()
        show_build_summary()
    else:
        print("❌ BUILD FAILED: No executables were created successfully")
        sys.exit(1)

if __name__ == "__main__":
    main()
