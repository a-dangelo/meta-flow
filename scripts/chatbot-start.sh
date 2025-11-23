#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.chatbot.yml}

# Force compose to build services one at a time to reduce RAM/CPU spikes.
export COMPOSE_PARALLEL_LIMIT=${COMPOSE_PARALLEL_LIMIT:-1}

echo "Building chatbot stack (progressive) using ${COMPOSE_FILE}..."
# Build services (use DOCKER_BUILD_NO_CACHE=1 to force rebuild)
if [ "${DOCKER_BUILD_NO_CACHE:-0}" = "1" ]; then
    echo "Building with --no-cache..."
    docker compose -f "${COMPOSE_FILE}" build --no-cache
else
    docker compose -f "${COMPOSE_FILE}" build
fi

echo "Starting chatbot stack..."
docker compose -f "${COMPOSE_FILE}" up -d
docker compose -f "${COMPOSE_FILE}" ps

echo ""
echo "Chatbot stack is running!"
echo "  Frontend: http://127.0.0.1:3002"
echo "  Backend:  http://127.0.0.1:8001"
