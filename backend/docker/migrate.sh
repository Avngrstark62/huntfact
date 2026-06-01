#!/usr/bin/env sh
set -eu

echo "Running database migrations..."
alembic upgrade head
echo "Database migrations complete."
