#!/bin/bash

set -e

echo "Running database migrations..."

cd /app/models/db_schemes/insurance_rag/

/app/.venv/bin/alembic upgrade head

cd /app

exec "$@"