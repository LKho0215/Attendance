# Docker Stop Script for Attendance System
# This script stops and removes the attendance system container

Write-Host "Stopping Attendance System..." -ForegroundColor Yellow

docker stop attendance-kiosk
docker rm attendance-kiosk

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container stopped and removed!" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to stop container!" -ForegroundColor Red
}

Write-Host ""
Write-Host "Current containers:" -ForegroundColor Cyan
docker ps -a