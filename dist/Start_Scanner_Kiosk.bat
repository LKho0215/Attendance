@echo off
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
