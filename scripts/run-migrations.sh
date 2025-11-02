#!/bin/bash

# Script to run database migrations locally
# This script should be run from the project root

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Running Database Migrations...${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

cd "$BACKEND_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/update dependencies if needed
if ! python -c "import alembic" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
fi

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

# Check if PostgreSQL is accessible
echo -e "${GREEN}Checking database connection...${NC}"
if ! python -c "
import psycopg2
conn = psycopg2.connect(
    host='$POSTGRES_HOST',
    port=$POSTGRES_PORT,
    database='$POSTGRES_DB',
    user='$POSTGRES_USER',
    password='$POSTGRES_PASSWORD'
)
conn.close()
print('Database connection successful!')
" 2>/dev/null; then
    echo -e "${RED}Error: Cannot connect to database!${NC}"
    echo -e "${YELLOW}Please make sure:${NC}"
    echo -e "  1. PostgreSQL container is running: docker ps | grep postgres"
    echo -e "  2. Database credentials are correct"
    exit 1
fi

# Show current migration status
echo -e "${GREEN}Current migration status:${NC}"
alembic current || echo "No migrations applied yet"

# Run migrations
echo -e "${GREEN}Running migrations...${NC}"
if alembic upgrade head; then
    echo -e "${GREEN}✓ Migrations completed successfully!${NC}"
    
    # Show current revision after migration
    echo -e "${GREEN}Current database revision:${NC}"
    alembic current
else
    echo -e "${RED}✗ Migration failed!${NC}"
    exit 1
fi

