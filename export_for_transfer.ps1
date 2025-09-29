# Export Attendance System for Transfer
# This script prepares everything needed to transfer to another PC

Write-Host "🚚 Preparing Attendance System for Transfer..." -ForegroundColor Green
Write-Host ""

# Check if Docker image exists
$imageExists = docker images attendance-system -q
if (-not $imageExists) {
    Write-Host "❌ attendance-system image not found!" -ForegroundColor Red
    Write-Host "Please build the image first: docker build -t attendance-system ." -ForegroundColor Yellow
    exit 1
}

# Create export directory
$exportDir = "transfer_package"
if (Test-Path $exportDir) {
    Remove-Item $exportDir -Recurse -Force
}
New-Item -ItemType Directory -Path $exportDir | Out-Null

Write-Host "📦 Exporting Docker image..." -ForegroundColor Yellow
docker save -o "$exportDir/attendance-system.tar" attendance-system

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker image exported successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to export Docker image!" -ForegroundColor Red
    exit 1
}

# Copy essential files
Write-Host "📋 Copying essential files..." -ForegroundColor Yellow

# Copy data folder (if exists)
if (Test-Path "data") {
    Copy-Item "data" -Destination "$exportDir/" -Recurse
    Write-Host "✅ Data folder copied" -ForegroundColor Green
} else {
    Write-Host "⚠️  No data folder found" -ForegroundColor Yellow
}

# Copy management scripts
$scripts = @("docker_run.ps1", "docker_stop.ps1", "docker_build.ps1")
foreach ($script in $scripts) {
    if (Test-Path $script) {
        Copy-Item $script -Destination "$exportDir/"
        Write-Host "✅ $script copied" -ForegroundColor Green
    }
}

# Copy guide
if (Test-Path "TRANSFER_GUIDE.md") {
    Copy-Item "TRANSFER_GUIDE.md" -Destination "$exportDir/"
    Write-Host "✅ Transfer guide copied" -ForegroundColor Green
}

# Create setup script for new PC
$setupScript = @"
# Setup Script for New PC
# Run this script after copying the transfer package

Write-Host "🚀 Setting up Attendance System..." -ForegroundColor Green

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found! Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Load Docker image
Write-Host "📥 Loading Docker image..." -ForegroundColor Yellow
docker load -i attendance-system.tar

if (`$LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker image loaded successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 Setup complete! You can now run:" -ForegroundColor Green
    Write-Host "   docker run -d --name attendance-kiosk -v `"`${PWD}/data:/app/data`" attendance-system" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or use the management scripts:" -ForegroundColor Yellow
    Write-Host "   ./docker_run.ps1    # Start the system" -ForegroundColor Cyan
    Write-Host "   ./docker_stop.ps1   # Stop the system" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to load Docker image!" -ForegroundColor Red
}
"@

$setupScript | Out-File -FilePath "$exportDir/setup_new_pc.ps1" -Encoding UTF8

# Get sizes
$tarSize = [math]::Round((Get-Item "$exportDir/attendance-system.tar").Length / 1MB, 1)
$totalSize = [math]::Round((Get-ChildItem $exportDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)

Write-Host ""
Write-Host "📊 Export Summary:" -ForegroundColor Cyan
Write-Host "   Docker image: $tarSize MB" -ForegroundColor White
Write-Host "   Total package: $totalSize MB" -ForegroundColor White
Write-Host "   Location: $exportDir/" -ForegroundColor White
Write-Host ""
Write-Host "📋 Files in transfer package:" -ForegroundColor Cyan
Get-ChildItem $exportDir -Recurse | ForEach-Object {
    $size = if ($_.PSIsContainer) { "DIR" } else { "$([math]::Round($_.Length/1MB,1)) MB" }
    Write-Host "   $($_.Name) ($size)" -ForegroundColor White
}

Write-Host ""
Write-Host "🎯 Next Steps:" -ForegroundColor Green
Write-Host "1. Copy the '$exportDir' folder to your new PC" -ForegroundColor White
Write-Host "2. Install Docker Desktop on the new PC" -ForegroundColor White
Write-Host "3. Run 'setup_new_pc.ps1' in the copied folder" -ForegroundColor White
Write-Host ""
Write-Host "✅ Export complete!" -ForegroundColor Green