# Docker Build Script for Attendance System
# This script builds the Docker image for the attendance system

Write-Host "Building Attendance System Docker Image..." -ForegroundColor Green
docker build -t attendance-system .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host "Image size:" -ForegroundColor Yellow
    docker images attendance-system
} else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
}