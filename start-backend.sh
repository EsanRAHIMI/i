#!/bin/bash
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
export POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_DB=i_DB POSTGRES_USER=esan POSTGRES_PASSWORD=Admin_1234_1234 REDIS_URL=redis://localhost:6379/0 MINIO_ENDPOINT=localhost:9000 MINIO_ACCESS_KEY=esan MINIO_SECRET_KEY=Admin_1234_1234 PYTHONPATH=$(pwd) TESTING=false
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
