#!/bin/sh
set -e

echo "Stopping containers..."
docker compose down

echo "Pulling latest images..."
docker compose pull

echo "Starting containers..."
docker compose up -d

echo "Logs (last 20 lines)..."
docker compose logs --tail=20
