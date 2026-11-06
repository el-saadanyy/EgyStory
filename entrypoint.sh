#!/bin/sh
set -e

# Pre-seed persistent volume with existing sqlite database if needed
if [ -n "$DATABASE_PATH" ]; then
    DB_DIR=$(dirname "$DATABASE_PATH")
    mkdir -p "$DB_DIR"
    if [ ! -f "$DATABASE_PATH" ] && [ -f "/app/db.sqlite3" ]; then
        echo "--> Pre-seeding persistent database from initial db.sqlite3..."
        cp /app/db.sqlite3 "$DATABASE_PATH"
    fi
fi

# Pre-seed persistent media directory if mounted separately
if [ -n "$MEDIA_ROOT_PATH" ]; then
    mkdir -p "$MEDIA_ROOT_PATH"
    if [ -d "/app/media" ] && [ ! "$(ls -A "$MEDIA_ROOT_PATH" 2>/dev/null)" ]; then
        echo "--> Pre-seeding persistent media directory from initial media files..."
        cp -r /app/media/* "$MEDIA_ROOT_PATH"/ 2>/dev/null || true
    fi
fi

# Run database migrations
echo "--> Running database migrations..."
python manage.py migrate --noinput

# Synchronize permanent demo media to storage
echo "--> Synchronizing demo media..."
python manage.py sync_demo_media || true

# Collect static files
echo "--> Collecting static files..."
python manage.py collectstatic --noinput

# Initialize demo accounts if requested
if [ "$INIT_DEMO_ACCOUNTS" = "true" ] || [ "$INIT_DEMO_ACCOUNTS" = "1" ]; then
    echo "--> Setting up demo accounts..."
    python manage.py setup_demo_accounts || true
fi

# Determine port and worker configuration
PORT="${PORT:-8000}"
WORKERS="${GUNICORN_WORKERS:-2}"
THREADS="${GUNICORN_THREADS:-2}"

# If the command is gunicorn (or default empty), run optimized for Render Free (512MB RAM)
if [ "$1" = "gunicorn" ] || [ "$#" -eq 0 ]; then
    echo "--> Starting Gunicorn on 0.0.0.0:${PORT} (workers: ${WORKERS}, threads: ${THREADS})..."
    exec gunicorn egystory.wsgi:application \
        --bind "0.0.0.0:${PORT}" \
        --workers "${WORKERS}" \
        --threads "${THREADS}" \
        --max-requests 500 \
        --max-requests-jitter 50 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
fi

exec "$@"
