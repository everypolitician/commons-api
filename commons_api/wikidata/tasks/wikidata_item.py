import datetime
import logging

import celery
import itertools

from django.template import TemplateDoesNotExist
from django.template.loader import get_template

from commons_api.wikidata import utils
from commons_api.wikidata.tasks.base import with_periodic_queuing_task, get_wikidata_model_by_name

__all__ = ['refresh_labels', 'refresh_metadata']

logger = logging.getLogger(__name__)


@with_periodic_queuing_task
@celery.shared_task(bind=True, queue='wdqs')
@utils.queries_wikidata
def refresh_labels(self, app_label, model, ids=None, queued_at=None, rate_limiting_handler=None):
    queryset = get_wikidata_model_by_name(app_label, model).objects.all()
    if queued_at is not None:
        queryset = queryset.filter(refresh_labels_last_queued=queued_at)
    if ids is not None:
        queryset = queryset.objects.filter(id__in=ids)
    for items in utils.split_every(queryset, 250):
        items = {item.id: item for item in items}
        results = utils.templated_wikidata_query('wikidata/query/labels.rq',
                                                 {'ids': sorted(items)},
                                                 rate_limiting_handler)
        for id, rows in itertools.groupby(results['results']['bindings'],
                                            key=lambda row: row['id']['value']):
            id = utils.item_uri_to_id(id)
            rows = list(rows)
            items[id].labels = {row['label']['xml:lang']: row['label']['value']
                                for row in rows}
            items[id].save()


@with_periodic_queuing_task
@celery.shared_task(bind=True, queue='wdqs')
@utils.queries_wikidata
def refresh_metadata(self, app_label, model, queued_at=None, rate_limiting_handler=None):
    template_name = f'{app_label}/query/{model}_metadata.rq'
    try:
        get_template(template_name)
    except TemplateDoesNotExist:
        return

    queryset = get_wikidata_model_by_name(app_label, model).objects.all()
    if queued_at is not None:
        queryset = queryset.filter(refresh_metadata_last_queued=queued_at)
    for items in utils.split_every(queryset, 250):
        items = {item.id: item for item in items}
        results = utils.templated_wikidata_query(template_name,
                                                 {'ids': sorted(items)},
                                                 rate_limiting_handler)
        vars = {var for var in results['head']['vars'] if var != 'id' and not var.endswith('Label')}
        for id, rows in itertools.groupby(results['results']['bindings'],
                                          key=lambda row: row['id']['value']):
            id = utils.item_uri_to_id(id)
            rows = list(rows)
            try:
                items[id].update_from_metadata(rows, vars)
                items[id].save()
            except Exception:
                logger.exception("Failed to update metadata for %s.%s %s (using %r)", app_label, model, id, rows)
