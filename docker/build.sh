#!/bin/bash
# Build script for Docker deployment

set -e

echo "🚀 Building EPANET Docker containers..."

# Build frontend first (needed for nginx)
echo "📦 Building frontend..."
docker-compose build frontend

# Build backend services
echo "📦 Building backend services..."
docker-compose build backend leak-detection-api

# Build nginx (no build needed, using image)
echo "✅ Build completed!"

echo ""
echo "📋 Next steps:"
echo "1. Update YOUR_SERVER_IP in docker-compose.prod.yml"
echo "2. Run: docker-compose -f docker-compose.prod.yml up -d"
echo "3. Check logs: docker-compose logs -f"

