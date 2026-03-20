#!/bin/bash
# i-Assistant Start up script for macOS (Opens multiple terminal tabs)

echo "========================================================"
echo "🚀 Starting i-Assistant Local Development Environment..."
echo "========================================================"

# 1. Start Infrastructure (Postgres, Redis, MinIO)
echo "📦 Starting infra services (Postgres, Redis, MinIO) via Docker..."
docker-compose up -d

echo "⏳ Waiting for databases to be ready..."
sleep 3

# 2. Get absolute path of this project
PROJECT_ROOT=$(pwd)

# 3. Open Terminal tabs for each service using AppleScript
echo "📡 Starting Auth Service in a new terminal tab..."
osascript -e 'tell application "Terminal"
    do script "cd \"'$PROJECT_ROOT'/auth\" && if [ ! -d \".venv-auth\" ]; then python3 -m venv .venv-auth && source .venv-auth/bin/activate && pip install -r requirements.txt; fi && source .venv-auth/bin/activate && set -a && source ../.env && set +a && uvicorn auth_service.main:app --host 0.0.0.0 --port 8001 --reload"
end tell'

echo "⚙️ Starting Backend Service in a new terminal tab..."
osascript -e 'tell application "Terminal"
    do script "cd \"'$PROJECT_ROOT'/backend\" && if [ ! -d \"venv\" ]; then python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt; fi && source venv/bin/activate && set -a && source ../.env && set +a && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
end tell'

echo "🎨 Starting Frontend Service in a new terminal tab..."
osascript -e 'tell application "Terminal"
    do script "cd \"'$PROJECT_ROOT'/frontend\" && npm install && npm run dev"
end tell'

echo "✅ All local services have been initialized in separate tabs!"
echo "   - Auth API:     http://localhost:8001/v1/docs"
echo "   - Backend API:  http://localhost:8000/api/v1/docs"
echo "   - Frontend UI:  http://localhost:3000"
echo "========================================================"
