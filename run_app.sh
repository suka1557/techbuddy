#!/bin/bash

# --- CONFIGURATION (The Source of Truth) ---
# -------------------------
# APPLICATION CONFIG
# -------------------------
export ENVIRONMENT="docker"  # This will tell our app to load docker.yaml config
if [ "$ENVIRONMENT" = "docker" ]; then
    echo "[*] Running in Docker environment. Loading docker.yaml configuration."
    # Create shared network if it doesn't exist
    if ! docker network ls | grep -q "shared_network"; then
        echo "[*] Creating Docker network: shared_network"
        docker network create shared_network
    fi
else
    echo "[*] Running in non-Docker environment. Please set ENVIRONMENT=docker to load docker.yaml configuration."
fi

# -------------------------
# POSTGRES CONFIG
# -------------------------
export DB_NAME="techbuddy_db"
export DB_USER="admin"
export DB_PASS="password123"
export SCHEMA_NAME="techbuddy"
export DB_PORT=5300
export APP_PORT=8000
export DB_HOST="postgres"  # This should match the service name in docker-compose.yml


# -------------------------
# MINIO CONFIG
# -------------------------
export MINIO_API_PORT=9000
export MINIO_CONSOLE_PORT=9001
export MINIO_ROOT_USER="admin"
export MINIO_ROOT_PASSWORD="minioadmin123"

# Load secrets from .env file if it exists (optional, for local overrides)
if [ -f .env ]; then
    echo "[*] Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo "[*] No .env file found. Using default environment variables."
fi

# Cleanup function
cleanup() {
    echo -e "\n\n[~] Shutting down TechBuddy..."
    docker compose down -v
    echo "[+] Cleanup complete."
    exit
}

trap cleanup SIGINT

echo "[+] Initializing TechBuddy with User: $DB_USER"
echo "[+] Database Port: $DB_PORT | App Port: $APP_PORT"

# docker compose automatically sees 'export' variables from this shell
docker compose up --build -d

echo "[+] TechBuddy containers started in detached mode"
echo "[*] To view logs, run: docker compose logs -f app"