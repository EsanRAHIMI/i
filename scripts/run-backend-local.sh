#!/bin/bash

# Script to run backend locally (outside Docker)
# This allows for faster development without Docker image rebuilds

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Starting Backend in Local Mode...${NC}"
echo -e "${BLUE}========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

cd "$BACKEND_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python 3.11 virtual environment...${NC}"
    # Try python3.11 first, fallback to python3 if not available
    if command -v python3.11 &> /dev/null; then
        python3.11 -m venv venv
    else
        python3 -m venv venv
        echo -e "${YELLOW}Warning: python3.11 not found, using python3. Make sure it's Python 3.11+${NC}"
    fi
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/update dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Set environment variables for local development
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=i_DB
export POSTGRES_USER=esan
export POSTGRES_PASSWORD=Admin_1234_1234
export REDIS_URL=redis://localhost:6379/0
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=esan
export MINIO_SECRET_KEY=Admin_1234_1234
export PYTHONPATH="$BACKEND_DIR"
export TESTING=false

# Create logs directory if it doesn't exist
mkdir -p logs

# Run database migrations
echo -e "${GREEN}Running database migrations...${NC}"
alembic upgrade head || echo -e "${YELLOW}Warning: Migration check failed, continuing anyway...${NC}"

# Check if services are running
echo -e "${GREEN}Checking Docker services...${NC}"

# Check PostgreSQL - be more flexible with status check
POSTGRES_STATUS=$(docker ps --format "{{.Status}}" --filter "name=i-postgres" 2>/dev/null || echo "")
if [ -z "$POSTGRES_STATUS" ] || ! echo "$POSTGRES_STATUS" | grep -qi "Up"; then
    echo -e "${RED}Error: PostgreSQL container (i-postgres) is not running!${NC}"
    echo -e "${YELLOW}Status: $POSTGRES_STATUS${NC}"
    echo -e "${YELLOW}Please start Docker services: docker-compose up -d${NC}"
    exit 1
fi
# Verify PostgreSQL is actually accepting connections
if ! docker exec i-postgres pg_isready -U esan -h localhost > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Warning: PostgreSQL container is running but not accepting connections yet${NC}"
    echo -e "${YELLOW}Waiting a bit more...${NC}"
    sleep 3
fi
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

# Check Redis - just warn if not running
REDIS_STATUS=$(docker ps --format "{{.Status}}" --filter "name=i-redis" 2>/dev/null || echo "")
if [ -z "$REDIS_STATUS" ] || ! echo "$REDIS_STATUS" | grep -qi "Up"; then
    echo -e "${YELLOW}⚠ Warning: Redis container (i-redis) may not be running${NC}"
    echo -e "${YELLOW}Status: $REDIS_STATUS${NC}"
else
    echo -e "${GREEN}✓ Redis is running${NC}"
fi

# Check if port 8000 is available
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}Warning: Port 8000 is already in use!${NC}"
    echo -e "${YELLOW}Killing existing process...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start the backend server
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Starting FastAPI server...${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Backend will be available at: http://localhost:8000${NC}"
echo -e "${GREEN}✓ Health check: http://localhost:8000/health${NC}"
echo -e "${GREEN}✓ API documentation: http://localhost:8000/api/v1/docs${NC}"
echo -e "${GREEN}✓ Nginx will proxy requests from http://localhost/api -> http://localhost:8000${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info

