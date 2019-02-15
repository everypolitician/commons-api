import os

from celery import Celery
from django.apps import apps

app = Celery(__package__)

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: [n.name for n in apps.get_app_configs()])

app.conf.beat_schedule = {
    # Wholesale updates
    'update-countries-daily': {
        'task': 'commons_api.wikidata.tasks.country.refresh_country_list',
        'schedule': 60 * 60 * 24,
    },
    'refresh-labels-periodically': {
        'task': 'commons_api.wikidata.tasks.wikidata_item.refresh_labels_queue_periodically',
        'schedule': 60,
    },
    'refresh-metadata-periodically': {
        'task': 'commons_api.wikidata.tasks.wikidata_item.refresh_metadata_queue_periodically',
        'schedule': 60,
        'kwargs': {'not_queued_in': 3600 * 24 * 14},
    },
    'refresh-legislatures-periodically': {
        'task': 'commons_api.wikidata.tasks.legislature.refresh_legislatures_queue_periodically',
        'schedule': 60,
    },
    'refresh-members-periodically': {
        'task': 'commons_api.wikidata.tasks.legislature.refresh_members_queue_periodically',
        'schedule': 60,
    },
    'refresh-districts-periodically': {
        'task': 'commons_api.wikidata.tasks.legislature.refresh_districts_queue_periodically',
        'schedule': 60,
    },
}
