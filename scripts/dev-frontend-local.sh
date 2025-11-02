#!/bin/bash

# Script for local frontend development (fastest hot reload)
# This runs Next.js dev server directly on your machine (no Docker)

set -e

echo "🚀 Starting Frontend Development (Local Mode)..."
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")/../frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "📝 Creating .env.local file..."
    cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost/ws
NODE_ENV=development
EOF
    echo "✅ Created .env.local"
    echo ""
fi

# Start development server
echo "✨ Starting Next.js development server..."
echo "🌐 Access: http://localhost:3000"
echo "🔄 Hot reload is ENABLED - changes will appear instantly!"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev

