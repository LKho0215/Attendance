@echo off
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
