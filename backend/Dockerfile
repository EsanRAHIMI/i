# Multi-stage build for Python backend
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# - gcc, g++: Required for compiling Python packages (psycopg2, cryptography, etc.)
# - curl: Required for health checks
# - wget: Alternative for health checks and downloads
# - ffmpeg: Required for pydub audio processing
# - libsndfile1: Required for soundfile/librosa audio processing
# - sox: Audio processing tools
# - build-essential: Additional build tools for native extensions
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    ffmpeg \
    libsndfile1 \
    sox \
    libsox-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory and set permissions
RUN mkdir -p logs && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
