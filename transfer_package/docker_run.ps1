# Docker Run Script for Attendance System
# This script runs the attendance system in a Docker container

Write-Host "Starting Attendance System..." -ForegroundColor Green

# Stop and remove existing container if it exists
docker stop attendance-kiosk 2>$null
docker rm attendance-kiosk 2>$null

# Run the container with volume mounts for data persistence
docker run -d `
    --name attendance-kiosk `
    -v "${PWD}/data:/app/data" `
    -v "${PWD}/exports:/app/exports" `
    --device=/dev/video0:/dev/video0 `
    -e DISPLAY=$env:DISPLAY `
    attendance-system

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container started successfully!" -ForegroundColor Green
    Write-Host "Container status:" -ForegroundColor Yellow
    docker ps -f name=attendance-kiosk
    Write-Host ""
    Write-Host "To see logs: docker logs attendance-kiosk" -ForegroundColor Cyan
    Write-Host "To stop: docker stop attendance-kiosk" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to start container!" -ForegroundColor Red
}