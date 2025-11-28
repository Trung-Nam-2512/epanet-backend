#!/bin/bash
# Deployment script for production

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying EPANET Application${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating template...${NC}"
    cat > .env << EOF
MAPBOX_TOKEN=your_mapbox_token_here
EOF
    echo -e "${YELLOW}Please update .env with your actual values${NC}"
fi

# Check if required files exist
echo "📋 Checking required files..."
REQUIRED_FILES=(
    "models/leak_detection_model_local.pkl"
    "models/model_metadata.json"
    "epanetVip1.inp"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Missing required file: $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All required files present${NC}"

# Get server IP
read -p "Enter your server IP address: " SERVER_IP

if [ -z "$SERVER_IP" ]; then
    echo -e "${RED}❌ Server IP is required${NC}"
    exit 1
fi

# Update docker-compose.prod.yml with server IP
echo "📝 Updating configuration with server IP: $SERVER_IP"
sed -i.bak "s/YOUR_SERVER_IP/$SERVER_IP/g" docker-compose.prod.yml

# Build containers
echo ""
echo "🔨 Building containers..."
docker-compose -f docker-compose.prod.yml build

# Start containers
echo ""
echo "🚀 Starting containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo ""
echo "🏥 Checking service health..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo ""
echo "📋 Access your application:"
echo "   Frontend: http://$SERVER_IP:1437"
echo "   Backend API: http://$SERVER_IP:1438/api/v1"
echo "   Health Check: http://$SERVER_IP:1438/health"
echo ""
echo "📊 View logs:"
echo "   docker-compose -f docker-compose.prod.yml logs -f"

