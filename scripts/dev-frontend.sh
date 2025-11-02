#!/bin/bash

# Script for quick frontend development
# This script rebuilds only the frontend container for faster development

set -e

echo "🚀 Starting Frontend Development Mode..."

# Check if we're using dev compose file
if docker-compose -f docker-compose.dev.yml ps frontend 2>/dev/null | grep -q "running"; then
    echo "📦 Rebuilding frontend container only..."
    docker-compose -f docker-compose.dev.yml build frontend
    docker-compose -f docker-compose.dev.yml up -d frontend
    echo "✅ Frontend restarted! Changes will hot reload automatically."
    echo ""
    echo "📊 View logs: docker-compose -f docker-compose.dev.yml logs -f frontend"
    echo "🌐 Access: http://localhost:3000"
else
    echo "⚠️  Frontend container not running with dev config."
    echo "📦 Starting all services in development mode..."
    docker-compose -f docker-compose.dev.yml up -d --build frontend postgres redis minio
    echo "✅ Services started!"
    echo ""
    echo "📊 View logs: docker-compose -f docker-compose.dev.yml logs -f frontend"
    echo "🌐 Access: http://localhost:3000"
fi
