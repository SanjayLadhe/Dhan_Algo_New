#!/bin/bash

# Dhan Algo Trading Platform - Stop Script

echo "🛑 Stopping Dhan Algo Trading Platform..."

docker-compose down

echo ""
echo "✅ All services stopped successfully!"
echo ""
echo "💾 Data is preserved in Docker volumes."
echo "🔄 To start again, run: ./start.sh"
