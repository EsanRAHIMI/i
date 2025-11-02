#!/bin/bash

# Script to rebuild only the frontend service
# Usage: ./scripts/rebuild-frontend.sh [prod|dev]

set -e

MODE="${1:-dev}"

if [ "$MODE" = "prod" ]; then
    echo "🏭 Rebuilding frontend for PRODUCTION..."
    docker-compose build --no-cache frontend
    docker-compose up -d frontend
    echo "✅ Frontend rebuilt and restarted in production mode"
else
    echo "🔧 Rebuilding frontend for DEVELOPMENT..."
    docker-compose -f docker-compose.dev.yml build frontend
    docker-compose -f docker-compose.dev.yml up -d frontend
    echo "✅ Frontend rebuilt and restarted in development mode"
    echo ""
    echo "💡 Changes will hot reload automatically - no rebuild needed!"
fi

echo ""
echo "📊 View logs: docker-compose logs -f frontend"
