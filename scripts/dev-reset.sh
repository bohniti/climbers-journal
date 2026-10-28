#!/usr/bin/env bash
set -euo pipefail

DB_NAME="climbers_journal"

echo "=== Dev Reset ==="

# Kill FastAPI dev server (uvicorn)
if pgrep -f "uvicorn.*climbers_journal" > /dev/null 2>&1; then
  echo "Stopping FastAPI backend..."
  pkill -f "uvicorn.*climbers_journal" || true
else
  echo "Backend not running."
fi

# Kill Next.js dev server
if pgrep -f "next dev" > /dev/null 2>&1; then
  echo "Stopping Next.js frontend..."
  pkill -f "next dev" || true
else
  echo "Frontend not running."
fi

# Reset the database
if psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
  echo "Dropping database '$DB_NAME'..."
  dropdb "$DB_NAME"
else
  echo "Database '$DB_NAME' does not exist, skipping drop."
fi

echo "Creating database '$DB_NAME'..."
createdb "$DB_NAME"

echo "Running migrations..."
cd "$(dirname "$0")/../app/backend"
uv run alembic upgrade head

echo ""
echo "Done. Database is clean. Backend and frontend are stopped."
echo ""
echo "Next steps:"
echo "  1. Start backend:  cd app/backend && uv run fastapi dev climbers_journal/main.py"
echo "  2. Re-import data: POST /sync/intervals + POST /import/climbing-csv"
