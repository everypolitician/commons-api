release: python manage.py migrate
web: gunicorn commons_api.wsgi:application
worker: celery -A commons_api worker --without-heartbeat -X shapefiles -n default-worker@%h
# shapefiles_worker: celery -A commons_api worker --without-heartbeat -c 1 -Q shapefiles -n shapefiles-worker@%h --max-tasks-per-child=1

