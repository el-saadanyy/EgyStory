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

# Collect static files
echo "--> Collecting static files..."
python manage.py collectstatic --noinput

# Execute the main container process
echo "--> Starting web server on port ${PORT:-8000}..."
exec "$@"

