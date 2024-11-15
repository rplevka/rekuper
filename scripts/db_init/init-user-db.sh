#!/bin/bash
set -e

# Create the telemetry database and the telemetry role
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE telemetry;
    CREATE ROLE ${POSTGRES_RO_USER:-telemetry} WITH LOGIN PASSWORD '${POSTGRES_RO_PASSWORD:-changeme}';
    GRANT CONNECT ON DATABASE telemetry TO ${POSTGRES_RO_USER:-telemetry};
EOSQL

# Connect to the telemetry database to set up permissions and triggers
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "telemetry" <<-EOSQL
    GRANT USAGE ON SCHEMA public TO ${POSTGRES_RO_USER:-telemetry};

    -- Grant SELECT privileges on existing tables
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${POSTGRES_RO_USER:-telemetry};

    -- Set default privileges for future tables created by the postgres user
    ALTER DEFAULT PRIVILEGES FOR USER ${POSTGRES_USER} IN SCHEMA public GRANT SELECT ON TABLES TO ${POSTGRES_RO_USER:-telemetry};
EOSQL