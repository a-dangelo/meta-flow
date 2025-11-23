#!/usr/bin/env bash
set -euo pipefail

# Color codes for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Meta-Flow Service Stopper ===${NC}"
echo ""

# Check which services are running
META_AGENT_RUNNING=$(docker ps --filter "name=metaflow-frontend" --filter "name=metaflow-backend" --format "{{.Names}}" | wc -l)
CHATBOT_RUNNING=$(docker ps --filter "name=metaflow-chatbot" --format "{{.Names}}" | wc -l)

if [ "$META_AGENT_RUNNING" -eq 0 ] && [ "$CHATBOT_RUNNING" -eq 0 ]; then
    echo -e "${YELLOW}No Meta-Flow services are currently running.${NC}"
    exit 0
fi

echo "Currently running services:"
echo ""

if [ "$META_AGENT_RUNNING" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} Meta-Agent (ports 3001, 8000)"
fi

if [ "$CHATBOT_RUNNING" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} Chatbot (ports 3002, 8001)"
fi

echo ""
echo "Which service would you like to stop?"
echo ""

MENU_OPTION=1
if [ "$META_AGENT_RUNNING" -gt 0 ]; then
    echo "  $MENU_OPTION) Meta-Agent"
    META_OPTION=$MENU_OPTION
    MENU_OPTION=$((MENU_OPTION + 1))
fi

if [ "$CHATBOT_RUNNING" -gt 0 ]; then
    echo "  $MENU_OPTION) Chatbot"
    CHATBOT_OPTION=$MENU_OPTION
    MENU_OPTION=$((MENU_OPTION + 1))
fi

if [ "$META_AGENT_RUNNING" -gt 0 ] && [ "$CHATBOT_RUNNING" -gt 0 ]; then
    echo "  $MENU_OPTION) Both services"
    BOTH_OPTION=$MENU_OPTION
fi

echo ""
echo -e "  ${YELLOW}q) Quit${NC}"
echo ""

# Read user choice
read -p "Enter your choice: " choice

# Handle quit
if [ "$choice" = "q" ] || [ "$choice" = "Q" ]; then
    echo "Exiting..."
    exit 0
fi

# Process numeric choice
SHOULD_STOP_META=0
SHOULD_STOP_CHATBOT=0

if [ "$META_AGENT_RUNNING" -gt 0 ] && [ "$choice" = "${META_OPTION:-}" ]; then
    SHOULD_STOP_META=1
fi

if [ "$CHATBOT_RUNNING" -gt 0 ] && [ "$choice" = "${CHATBOT_OPTION:-}" ]; then
    SHOULD_STOP_CHATBOT=1
fi

if [ "$META_AGENT_RUNNING" -gt 0 ] && [ "$CHATBOT_RUNNING" -gt 0 ] && [ "$choice" = "${BOTH_OPTION:-}" ]; then
    SHOULD_STOP_META=1
    SHOULD_STOP_CHATBOT=1
fi

# Execute stops
if [ "$SHOULD_STOP_META" -eq 1 ]; then
    echo ""
    echo -e "${RED}Stopping Meta-Agent...${NC}"
    bash "$(dirname "$0")/meta-agent-stop.sh"
fi

if [ "$SHOULD_STOP_CHATBOT" -eq 1 ]; then
    echo ""
    echo -e "${RED}Stopping Chatbot...${NC}"
    bash "$(dirname "$0")/chatbot-stop.sh"
fi

if [ "$SHOULD_STOP_META" -eq 0 ] && [ "$SHOULD_STOP_CHATBOT" -eq 0 ]; then
    echo -e "${YELLOW}Invalid choice. Please run the script again.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Done!${NC}"
