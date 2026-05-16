#!/bin/sh
set -e

if [ -n "$DB_HOST" ]; then
    echo "Waiting for postgres..."

    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.5
    done

    echo "PostgreSQL started"
fi

if [ "$RUN_MIGRATIONS" = "true" ]; then
    # Run migrations
    python manage.py migrate
fi

# Create admin users if needed (legacy code from bootstrap)
# python manage.py bootstrap user1,user2...

exec "$@"
