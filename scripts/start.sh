#!/bin/bash

# Meta-Flow Docker Startup Script
# Purpose: Build and start the entire system with Docker Compose

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}     Meta-Flow Docker Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed!${NC}"
    echo -e "${YELLOW}Please install Docker: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    # Try docker compose (v2 syntax)
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}ERROR: Docker Compose is not installed!${NC}"
        echo -e "${YELLOW}Please install Docker Compose: https://docs.docker.com/compose/install/${NC}"
        exit 1
    fi
    # Use docker compose v2 syntax
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found!${NC}"
    echo -e "${YELLOW}Creating .env from template...${NC}"

    # Copy template if it exists
    if [ -f .env.docker.example ]; then
        cp .env.docker.example .env
        echo -e "${GREEN}Created .env file from template${NC}"
        echo -e "${RED}IMPORTANT: Please edit .env and add your API key(s)${NC}"
        echo -e "${YELLOW}Required: At least one of ANTHROPIC_API_KEY, AIMLAPI_KEY, or GEMINI_API_KEY${NC}"
        echo ""
        echo -e "Edit the file with: ${GREEN}nano .env${NC} or ${GREEN}vim .env${NC}"
        exit 1
    else
        echo -e "${RED}ERROR: .env.docker.example not found!${NC}"
        exit 1
    fi
fi

# Check if at least one API key is set
API_KEY_FOUND=false
if grep -q "^ANTHROPIC_API_KEY=..*" .env 2>/dev/null; then
    echo -e "${GREEN}✓ Anthropic API key found${NC}"
    API_KEY_FOUND=true
fi
if grep -q "^AIMLAPI_KEY=..*" .env 2>/dev/null; then
    echo -e "${GREEN}✓ AIMLAPI key found${NC}"
    API_KEY_FOUND=true
fi
if grep -q "^GEMINI_API_KEY=..*" .env 2>/dev/null; then
    echo -e "${GREEN}✓ Gemini API key found${NC}"
    API_KEY_FOUND=true
fi

if [ "$API_KEY_FOUND" = false ]; then
    echo -e "${RED}ERROR: No valid API key found in .env file!${NC}"
    echo -e "${YELLOW}Please add at least one API key to .env:${NC}"
    echo -e "  - ANTHROPIC_API_KEY=sk-ant-..."
    echo -e "  - AIMLAPI_KEY=..."
    echo -e "  - GEMINI_API_KEY=..."
    echo ""
    echo -e "Edit the file with: ${GREEN}nano .env${NC} or ${GREEN}vim .env${NC}"
    exit 1
fi

# Parse command line arguments
BUILD_FLAG="--build"
DETACH_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-build)
            BUILD_FLAG=""
            shift
            ;;
        -d|--detach)
            DETACH_FLAG="-d"
            shift
            ;;
        --help)
            echo "Usage: ./start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-build    Start without rebuilding images"
            echo "  -d, --detach  Run in background (detached mode)"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: ./start.sh [--no-build] [-d|--detach]"
            exit 1
            ;;
    esac
done

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
$DOCKER_COMPOSE down 2>/dev/null || true

# Build and start services
if [ -n "$BUILD_FLAG" ]; then
    echo -e "${YELLOW}Building Docker images (this may take a few minutes)...${NC}"
fi

echo -e "${YELLOW}Starting Meta-Flow services...${NC}"
$DOCKER_COMPOSE up $BUILD_FLAG $DETACH_FLAG

# If running in detached mode, show status
if [ -n "$DETACH_FLAG" ]; then
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}       Meta-Flow is starting!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo "Waiting for services to be healthy..."

    # Wait for backend health check
    echo -n "Backend: "
    for i in {1..30}; do
        if $DOCKER_COMPOSE ps | grep -q "metaflow-backend.*healthy"; then
            echo -e "${GREEN}✓ Healthy${NC}"
            break
        fi
        echo -n "."
        sleep 1
        if [ $i -eq 30 ]; then
            echo -e "${RED}✗ Failed to start${NC}"
            echo "Checking logs..."
            $DOCKER_COMPOSE logs --tail=20 backend
            exit 1
        fi
    done

    # Wait for frontend health check
    echo -n "Frontend: "
    for i in {1..15}; do
        if $DOCKER_COMPOSE ps | grep -q "metaflow-frontend.*healthy"; then
            echo -e "${GREEN}✓ Healthy${NC}"
            break
        fi
        echo -n "."
        sleep 1
        if [ $i -eq 15 ]; then
            echo -e "${RED}✗ Failed to start${NC}"
            echo "Checking logs..."
            $DOCKER_COMPOSE logs --tail=20 frontend
            exit 1
        fi
    done

    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}      Meta-Flow is ready!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "🌐 Frontend:  ${BLUE}http://localhost${NC}"
    echo -e "🔧 Backend:   ${BLUE}http://localhost:8000${NC}"
    echo -e "📚 API Docs:  ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "To view logs:  ${YELLOW}$DOCKER_COMPOSE logs -f${NC}"
    echo -e "To stop:       ${YELLOW}./stop.sh${NC} or ${YELLOW}$DOCKER_COMPOSE down${NC}"
    echo ""
fi