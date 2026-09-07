#!/bin/bash
set -e

cd /app

# `docker run <image> celery -A mysite worker` and friends bypass the web stack.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting nginx + gunicorn..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/app.conf
