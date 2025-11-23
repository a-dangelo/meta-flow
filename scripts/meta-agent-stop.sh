#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}

echo "Stopping meta-agent stack using ${COMPOSE_FILE}..."
docker compose -f "${COMPOSE_FILE}" down
