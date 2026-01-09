#!/bin/bash
set -e

export PGHOST=postgres
export PGUSER=root
export PGPASSWORD=root
export PGDATABASE=postgres

until psql -c '\q'; do
  echo "Waiting for Postgres..."
  sleep 2
done

psql -f /docker-entrypoint-initdb.d/init-operations.sql
psql -d operations_service_db -f /docker-entrypoint-initdb.d/grant-operations.sql

echo "Initialization complete."
