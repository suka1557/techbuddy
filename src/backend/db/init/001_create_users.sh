#!/bin/bash
set -e

echo "[INIT] Running DB initialization script..."

# Use env variables directly here
psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<-EOSQL

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS ${SCHEMA_NAME};

-- Set search path
SET search_path TO ${SCHEMA_NAME};

-- Create table
CREATE TABLE IF NOT EXISTS ${SCHEMA_NAME}.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

EOSQL