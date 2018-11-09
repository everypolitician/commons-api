release: psql -c "CREATE EXTENSION IF NOT EXISTS hstore;"
release: python manage.py migrate
web: gunicorn commons_api.wsgi:application
worker: celery -A commons_api worker
