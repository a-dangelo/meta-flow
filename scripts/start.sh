#!/usr/bin/env bash
set -euo pipefail

# Color codes for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Meta-Flow Service Launcher ===${NC}"
echo ""
echo "Which service would you like to start?"
echo ""
echo "  1) Meta-Agent (Workflow Generator)"
echo "     - Frontend: http://127.0.0.1:3001"
echo "     - Backend:  http://127.0.0.1:8000"
echo ""
echo "  2) Chatbot (Interactive Workflow Assistant)"
echo "     - Frontend: http://127.0.0.1:3002"
echo "     - Backend:  http://127.0.0.1:8001"
echo ""
echo "  3) Both services"
echo ""
echo -e "  ${YELLOW}q) Quit${NC}"
echo ""

# Read user choice
read -p "Enter your choice [1-3, q]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}Starting Meta-Agent...${NC}"
        exec bash "$(dirname "$0")/meta-agent-start.sh"
        ;;
    2)
        echo ""
        echo -e "${GREEN}Starting Chatbot...${NC}"
        exec bash "$(dirname "$0")/chatbot-start.sh"
        ;;
    3)
        echo ""
        echo -e "${GREEN}Starting both services...${NC}"
        bash "$(dirname "$0")/meta-agent-start.sh"
        echo ""
        bash "$(dirname "$0")/chatbot-start.sh"
        ;;
    q|Q)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${YELLOW}Invalid choice. Please run the script again.${NC}"
        exit 1
        ;;
esac
