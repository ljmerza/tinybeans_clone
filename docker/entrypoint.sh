#!/bin/bash
set -e

cd /app

# `docker run <image> celery -A mysite worker` and friends bypass the web stack.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# RUN_MIGRATIONS=0 skips `migrate` so schema changes only happen when someone
# runs `manage.py migrate` on purpose (production does this). Default: migrate.
case "${RUN_MIGRATIONS:-1}" in
    0 | false | no | off)
        echo "RUN_MIGRATIONS=${RUN_MIGRATIONS}: skipping migrations."
        ;;
    *)
        echo "Running migrations..."
        python manage.py migrate --noinput
        ;;
esac

echo "Collecting static files..."
python manage.py collectstatic --noinput

# nginx must let through every upload the app accepts, so the app (not nginx)
# answers an oversized file with its own error. Derive the cap from settings.
echo "Setting the nginx upload cap..."
echo "client_max_body_size $(python manage.py upload_body_limit);" > /etc/nginx/upload-limit.conf

echo "Starting nginx + gunicorn..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/app.conf
