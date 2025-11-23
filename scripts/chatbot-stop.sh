#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.chatbot.yml}

echo "Stopping chatbot stack using ${COMPOSE_FILE}..."
docker compose -f "${COMPOSE_FILE}" down
