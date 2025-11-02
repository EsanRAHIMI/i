#!/bin/bash
# Quick Start Script for Development

echo "🚀 Starting Development Mode..."
echo ""
echo "Choose your method:"
echo "1) Local Frontend (Fastest - Recommended)"
echo "2) Docker Dev Mode (All services)"
echo ""
read -p "Enter choice [1 or 2]: " choice

case $choice in
  1)
    echo ""
    echo "✨ Starting Local Frontend Development..."
    ./scripts/dev-frontend-local.sh
    ;;
  2)
    echo ""
    echo "🐳 Starting Docker Development Mode..."
    docker-compose -f docker-compose.dev.yml up -d frontend postgres redis minio
    echo ""
    echo "✅ Services started!"
    echo "📊 View logs: docker-compose -f docker-compose.dev.yml logs -f frontend"
    echo "🌐 Access: http://localhost:3000"
    ;;
  *)
    echo "Invalid choice"
    exit 1
    ;;
esac
