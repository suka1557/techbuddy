#!/bin/bash

# --- CONFIGURATION (The Source of Truth) ---
export DB_NAME="techbuddy_db"
export DB_USER="admin"
export DB_PASS="password123"
export SCHEMA_NAME="techbuddy"
export DB_PORT=5300
export APP_PORT=8000
export DB_HOST="postgres"  # This should match the service name in docker-compose.yml
export ENVIRONMENT="docker"  # This will tell our app to load docker.yaml config

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