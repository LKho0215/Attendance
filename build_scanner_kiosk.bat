@echo off
title Build Scanner Kiosk Executable
echo ======================================
echo BUILDING SCANNER KIOSK EXECUTABLE
echo ======================================
echo.
echo This will create ScannerKiosk.exe
echo (QR/Barcode Scanner Only - No Camera)
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found!
    echo Please install Python or ensure it's in your PATH
    pause
    exit /b 1
)

REM Check if PyInstaller is available
python -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller not found!
    echo Installing PyInstaller...
    python -m pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo Building Scanner Kiosk executable...
echo.

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist\ScannerKiosk.exe del dist\ScannerKiosk.exe
if exist scanner_kiosk.spec del scanner_kiosk.spec

REM Build executable
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name=ScannerKiosk ^
    --add-data=data;data ^
    --add-data=assets;assets ^
    --add-data=core;core ^
    --hidden-import=PIL ^
    --hidden-import=customtkinter ^
    --hidden-import=numpy ^
    --hidden-import=tkinter ^
    --collect-all=customtkinter ^
    scanner_kiosk.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================
    echo BUILD SUCCESSFUL!
    echo ======================================
    echo.
    echo ScannerKiosk.exe created in dist\ folder
    echo File size: 
    for %%A in (dist\ScannerKiosk.exe) do echo %%~zA bytes
    echo.
    echo You can now copy dist\ScannerKiosk.exe to any Windows machine
    echo No Python installation required on target machine!
    echo.
) else (
    echo.
    echo ======================================
    echo BUILD FAILED!
    echo ======================================
    echo Check the error messages above
    echo.
)

pause
