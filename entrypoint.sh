#!/bin/bash
set -e

echo "Waiting for database..."
until python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.connect(('db', 5432))" 2>/dev/null; do
  echo "Database (db:5432) is unavailable - sleeping"
  sleep 1
done
echo "Database is up!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Loading seed data..."
python manage.py seed_data || echo "Seed data already loaded or failed - continuing..."

echo "Starting server..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --reload \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
