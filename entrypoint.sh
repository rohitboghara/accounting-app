#!/bin/bash
set -e

echo "Waiting for database..."

DB_HOST=$(python -c "from urllib.parse import urlparse; import os; url = urlparse(os.environ.get('DATABASE_URL', 'postgres://db:5432')); print(url.hostname)")
DB_PORT=$(python -c "from urllib.parse import urlparse; import os; url = urlparse(os.environ.get('DATABASE_URL', 'postgres://db:5432')); print(url.port or 5432)")

echo "Checking connection to $DB_HOST:$DB_PORT..."

until python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(2); s.connect(('$DB_HOST', int('$DB_PORT')))" 2>/dev/null; do
  echo "Database ($DB_HOST:$DB_PORT) is unavailable - sleeping"
  sleep 1
done

echo "Database is up!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Loading seed data..."
python manage.py seed_data || echo "Seed data already loaded or failed - continuing..."

echo "Starting server..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
