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
CREATE TABLE IF NOT EXISTS ${SCHEMA_NAME}.document_metadata (
    id SERIAL PRIMARY KEY,
    file_prefix VARCHAR,
    file_name VARCHAR,
    file_extension VARCHAR,
    page_number INTEGER,
    author VARCHAR,
    creation_date TIMESTAMP,
    mod_date TIMESTAMP,
    title VARCHAR,
    user_id VARCHAR,
    user_name VARCHAR,
    user_email VARCHAR,
    modified_by VARCHAR(100) DEFAULT 'Automated',
    modified_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

EOSQL