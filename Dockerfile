# Dockerfile for Attendance System
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-dri \
    libgl1-mesa-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p data/database data/faces data/temp exports

# Set environment variables
ENV PYTHONPATH=/app
ENV DISPLAY=:0

# Expose port for web interface (if needed later)
EXPOSE 8080

# Command to run the application
CMD ["python", "simple_kiosk.py"]