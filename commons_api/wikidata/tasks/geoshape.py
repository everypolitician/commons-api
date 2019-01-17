import datetime
import email.utils
import http.client
import json

import celery
from boundaries.models import Definition, Boundary
from boundaries.management.commands.loadshapefiles import Command as LoadShapefilesCommand
from django.contrib.gis.gdal import DataSource
from django.db import transaction
import requests

from .. import models
from .base import with_periodic_queuing_task, get_wikidata_model_by_name


@with_periodic_queuing_task(superclass=models.Spatial,
                            queryset_filter=lambda qs: qs.filter(geoshape_url__isnull=False))
@celery.shared_task
@transaction.atomic
def refresh_geoshape(app_label: str, model: str, id: str, queued_at):
    """Download a geoshape from wikidata"""

    model = get_wikidata_model_by_name(app_label, model, superclass=models.Spatial)
    instance = model.objects.get(id=id)  # type: models.Spatial

    if instance.refresh_geoshape_last_queued != queued_at:
        return {'result': 'since_requeued'}
    if not instance.geoshape_url:
        return {'result': 'unnecessary'}

    print(f"Importing {instance} from {instance.geoshape_url}")
    headers = {}
    if instance.geoshape_last_modified:
        headers['If-Modified-Since'] = email.utils.formatdate(instance.geoshape_last_modified.timestamp(), usegmt=True)
    response = requests.get(instance.geoshape_url, headers=headers)

    if response.status_code == http.client.NOT_MODIFIED:
        return {'result': 'not_modified'}
    response.raise_for_status()

    slug = instance.id + '-geoshape'

    data_source = DataSource(json.dumps(response.json()['data']))

    definition = Definition({'name': 'geoshape for {}'.format(instance.id),
                             'singular': 'boundary',
                             'encoding': 'utf-8',
                             'last_updated': datetime.datetime.now(),
                             'name_func': lambda feature: instance.id,
                             'id_func': lambda feature: instance.id,
                             'source_url': f"https://commons.wikimedia.org/wiki/{instance.geoshape_url}",
                             'licence_url': f"https://spdx.org/licenses/{response.json()['license']}",
                             'notes': f"Original source: {response.json()['sources']}",
                             })
    options = {'merge': None, 'clean': False}
    load_shapefiles_command = LoadShapefilesCommand()
    load_shapefiles_command.load_boundary_set(slug=slug,
                                              definition=definition,
                                              data_sources=[data_source],
                                              options=options)

    instance.boundary = Boundary.objects.get(
        set__slug=slug, external_id=instance.id
    )
    instance.geoshape_last_modified = email.utils.parsedate_to_datetime(response.headers['Last-Modified'])
    instance.save()

    return {'result': 'refreshed'}
