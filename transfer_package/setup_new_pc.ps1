# Setup Script for New PC
# Run this script after copying the transfer package

Write-Host "ðŸš€ Setting up Attendance System..." -ForegroundColor Green

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Host "âœ… Docker is installed" -ForegroundColor Green
} catch {
    Write-Host "âŒ Docker not found! Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Load Docker image
Write-Host "ðŸ“¥ Loading Docker image..." -ForegroundColor Yellow
docker load -i attendance-system.tar

if ($LASTEXITCODE -eq 0) {
    Write-Host "âœ… Docker image loaded successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "ðŸŽ‰ Setup complete! You can now run:" -ForegroundColor Green
    Write-Host "   docker run -d --name attendance-kiosk -v "${PWD}/data:/app/data" attendance-system" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or use the management scripts:" -ForegroundColor Yellow
    Write-Host "   ./docker_run.ps1    # Start the system" -ForegroundColor Cyan
    Write-Host "   ./docker_stop.ps1   # Stop the system" -ForegroundColor Cyan
} else {
    Write-Host "âŒ Failed to load Docker image!" -ForegroundColor Red
}
