#!/usr/bin/env sh
# Migration runner for Dokploy / Docker
set -e

echo "=========================================================="
echo "🚀 Starting Database Migrations..."
echo "=========================================================="

# Ensure we are in the right directory
cd /database

echo "⚙️ Running Backend migrations..."
alembic -c alembic.backend.ini upgrade head

echo "🔐 Running Auth migrations..."
alembic -c alembic.auth.ini upgrade head

echo "=========================================================="
echo "✅ Migrations completed successfully!"
echo "=========================================================="

# Keep the container alive so the user can access the terminal in Dokploy
echo "⏳ Keeping container alive for terminal access (tailing /dev/null)..."
tail -f /dev/null
