@echo off
title Build All Kiosk Executables
echo ========================================
echo BUILDING ALL KIOSK EXECUTABLES
echo ========================================
echo.
echo This will create both:
echo - SimpleKiosk.exe (Face Recognition + QR Scanner)
echo - ScannerKiosk.exe (QR/Barcode Scanner Only)
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found!
    echo Please install Python or ensure it's in your PATH
    pause
    exit /b 1
)

echo Starting comprehensive build process...
echo.

REM Run the Python build script
python build_executables.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ALL BUILDS COMPLETED SUCCESSFULLY!
    echo ========================================
    echo.
    echo Check the dist\ folder for:
    echo - SimpleKiosk.exe
    echo - ScannerKiosk.exe  
    echo - Start_Simple_Kiosk.bat
    echo - Start_Scanner_Kiosk.bat
    echo - Required data files and assets
    echo.
    echo Ready for deployment to any Windows machine!
    echo.
) else (
    echo.
    echo ========================================
    echo BUILD PROCESS FAILED!
    echo ========================================
    echo Check the error messages above
    echo.
)

pause
