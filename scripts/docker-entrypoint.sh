#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    echo "Seeding demo data..."
    python scripts/seed_demo.py
fi

echo "Starting application..."
exec "$@"
