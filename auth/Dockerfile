FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r authuser && useradd -r -g authuser authuser

# Set work directory
WORKDIR /app

# Copy auth service code
COPY . ./auth/

# Install auth service dependencies
RUN pip install --no-cache-dir --no-build-isolation -e ./auth

# Create logs directory and set permissions
RUN mkdir -p logs uploads/avatars && chown -R authuser:authuser /app

# Switch to non-root user
USER authuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command
ENV PORT=8001 \
    WEB_CONCURRENCY=2

CMD ["sh", "-c", "gunicorn auth_service.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8001} --workers ${WEB_CONCURRENCY:-2} --timeout 60"]
