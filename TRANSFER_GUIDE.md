# 🚚 How to Transfer Your Attendance System to Another PC

## Method 1: Docker Image Transfer (Recommended - No Internet Required)

### Step 1: Export the Image (On Current PC)
```powershell
# Save Docker image to file
docker save -o attendance-system.tar attendance-system
```
✅ **File created:** `attendance-system.tar` (about 1GB)

### Step 2: Transfer to New PC
Copy these files to the new PC:
- `attendance-system.tar` (the Docker image)
- `data/` folder (your face data and database)
- `docker_run.ps1`, `docker_stop.ps1` (optional management scripts)

### Step 3: Setup on New PC
```powershell
# 1. Install Docker Desktop on new PC
# 2. Load the image
docker load -i attendance-system.tar

# 3. Verify image is loaded
docker images

# 4. Run the system
docker run -d --name attendance-kiosk -v "${PWD}/data:/app/data" -v "${PWD}/exports:/app/exports" attendance-system
```

---

## Method 2: Complete Project Transfer (Easiest for Development)

### What to Copy:
Copy your entire `Attendance` folder to the new PC, including:
- All source code files
- `Dockerfile`
- `requirements.txt` 
- `data/` folder (face data & database)
- Docker scripts

### Setup on New PC:
```powershell
# 1. Install Docker Desktop
# 2. Navigate to copied folder
cd "C:\Users\NewUser\Desktop\Attendance"

# 3. Build the image
docker build -t attendance-system .

# 4. Run the system
docker run -d --name attendance-kiosk -v "${PWD}/data:/app/data" attendance-system
```

---

## Method 3: Docker Hub (Best for Multiple PCs)

### Step 1: Push to Docker Hub (One Time Setup)
```powershell
# 1. Create account at hub.docker.com
# 2. Login to Docker
docker login

# 3. Tag your image
docker tag attendance-system yourusername/attendance-system

# 4. Push to Docker Hub
docker push yourusername/attendance-system
```

### Step 2: Use on Any PC
```powershell
# Pull and run from anywhere
docker pull yourusername/attendance-system
docker run -d --name attendance-kiosk -v "${PWD}/data:/app/data" yourusername/attendance-system
```

---

## 📋 Quick Reference Commands

### On New PC (After transferring image):
```powershell
# Load the image
docker load -i attendance-system.tar

# Check if loaded
docker images

# Run the system
docker run -d --name attendance-kiosk -v "${PWD}/data:/app/data" attendance-system

# Check if running
docker ps

# View logs
docker logs attendance-kiosk

# Stop the system
docker stop attendance-kiosk
docker rm attendance-kiosk
```

## 🎯 Which Method Should You Use?

### Use **Method 1** (Docker Image Transfer) if:
- ✅ You want the fastest setup on new PC
- ✅ You don't want to rebuild the image
- ✅ You have limited internet on new PC
- ✅ One-time transfer

### Use **Method 2** (Complete Project) if:
- ✅ You want to modify code on new PC
- ✅ You want full development environment
- ✅ You plan to make changes

### Use **Method 3** (Docker Hub) if:
- ✅ You have multiple PCs to deploy to
- ✅ You want cloud-based sharing
- ✅ You want version control of images

## 💡 Pro Tips:

1. **Always transfer the `data/` folder** - Contains your registered faces and attendance records
2. **Install Docker Desktop first** on the new PC
3. **Use PowerShell as Administrator** for Docker commands
4. **Keep the same folder structure** for volume mounts to work properly

## 🔧 Troubleshooting:

**If image won't load:**
```powershell
# Check if file is corrupted
Get-FileHash attendance-system.tar
```

**If container won't start:**
```powershell
# Check Docker is running
docker version

# Check logs
docker logs attendance-kiosk
```

**If camera doesn't work:**
```powershell
# Add camera access (Linux/Mac)
docker run --device=/dev/video0 ...

# For Windows, may need different approach
```