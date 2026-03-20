#!/bin/bash
# i-Assistant Start up script for macOS
# Automatically opens terminal tabs for Auth, Backend, and Frontend

echo "========================================================"
echo "🚀 Starting i-Assistant Local Development Environment..."
echo "========================================================"

# 1. Ensure databases are up
echo "📦 Starting infra services (Postgres, Redis, MinIO) via Docker..."
docker-compose up -d

echo "⏳ Waiting 3 seconds for databases to initialize..."
sleep 3

PROJECT_ROOT=$(pwd)

# 2. Open Auth tab
echo "📡 Starting Auth Service in a new terminal tab..."
osascript -e 'tell application "Terminal"
    do script "cd \"'$PROJECT_ROOT'/auth\" && if [ ! -d \".venv-auth\" ]; then python3 -m venv .venv-auth; fi && source .venv-auth/bin/activate && pip install -r requirements.txt && export PYTHONPATH=src:\$PYTHONPATH && python -m uvicorn auth_service.main:app --host 0.0.0.0 --port 8001 --reload"
end tell'

# 3. Open Backend tab
echo "⚙️ Starting Backend Service in a new terminal tab..."
osascript -e 'tell application "Terminal"
    do script "cd \"'$PROJECT_ROOT'/backend\" && if [ ! -d \".venv\" ]; then python3 -m venv .venv; fi && source .venv/bin/activate && pip install -r requirements.txt && export PYTHONPATH=.:\$PYTHONPATH && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
end tell'

# 4. Open Frontend tab
echo "🎨 Starting Frontend Service in a new terminal tab..."
osascript -e 'tell application "Terminal"
    do script "cd \"'$PROJECT_ROOT'/frontend\" && npm install && npm run dev"
end tell'

echo "✅ All local services have been initialized in separate tabs!"
echo "   - Auth API:     http://localhost:8001/v1/docs"
echo "   - Backend API:  http://localhost:8000/api/v1/docs"
echo "   - Frontend UI:  http://localhost:3000"
echo "========================================================"
