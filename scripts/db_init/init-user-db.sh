#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE telemetry;
    CREATE ROLE telemetry WITH LOGIN PASSWORD 'changeme';
    GRANT CONNECT ON DATABASE telemetry TO telemetry;
    GRANT USAGE ON SCHEMA public TO telemetry;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO telemetry;
EOSQL
