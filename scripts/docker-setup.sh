#!/bin/bash

# Docker Setup Script for Production Environment
set -e

echo "🐳 Setting up Docker environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please review and update the values as needed."
fi

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p infra/nginx/conf.d
mkdir -p backend/logs
mkdir -p frontend/logs

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build --no-cache

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
services=("i-postgres" "i-redis" "i-minio" "i-backend" "i-frontend" "i-nginx")

for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
        docker logs "$service" --tail 20
    fi
done

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Services are available at:"
echo "  🌐 Frontend: http://localhost:3000"
echo "  🔧 Backend API: http://localhost:8000"
echo "  📊 Backend Docs: http://localhost:8000/api/v1/docs"
echo "  🗄️  PostgreSQL: localhost:5432"
echo "  🔴 Redis: localhost:6379"
echo "  📦 MinIO: http://localhost:9000 (Console: http://localhost:9001)"
echo ""
echo "To view logs: docker-compose logs -f [service-name]"
echo "To stop services: docker-compose down"
echo "To rebuild: docker-compose build --no-cache"