#!/bin/bash

# Dhan Algo Trading Platform - Quick Start Script

echo "🚀 Starting Dhan Algo Trading Platform..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ Please edit .env file with your configuration before proceeding."
    echo "📝 Run 'nano .env' or 'vim .env' to edit."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install it and try again."
    exit 1
fi

echo "📦 Building Docker images..."
docker-compose build

echo "🔧 Starting services..."
docker-compose up -d

echo ""
echo "✅ All services started successfully!"
echo ""
echo "📊 Access the application at:"
echo "   🌐 Web Dashboard:    http://localhost"
echo "   🎨 Frontend (Direct): http://localhost:3000"
echo "   🔌 Backend API:       http://localhost:8000"
echo "   📖 API Docs:          http://localhost:8000/docs"
echo ""
echo "📝 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo ""
echo "Happy Trading! 📈"
