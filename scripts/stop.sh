#!/bin/bash

# Meta-Flow Docker Stop Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Meta-Flow services...${NC}"

# Check which docker-compose command is available
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}ERROR: Docker Compose is not installed!${NC}"
    exit 1
fi

# Stop services
$DOCKER_COMPOSE down

echo -e "${GREEN}✓ All Meta-Flow services stopped successfully${NC}"
echo ""
echo -e "To restart: ${BLUE}./start.sh${NC}"