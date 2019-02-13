import datetime

import celery
import itertools

from commons_api.wikidata import utils
from commons_api.wikidata.tasks.base import with_periodic_queuing_task, get_wikidata_model_by_name

__all__ = ['refresh_labels']


@with_periodic_queuing_task
@celery.shared_task
def refresh_labels(app_label, model, ids=None, queued_at=None):
    """Refreshes all labels for the given model"""
    queryset = get_wikidata_model_by_name(app_label, model).objects.all()
    if queued_at is not None:
        queryset = queryset.filter(refresh_labels_last_queued=queued_at)
    if ids is not None:
        queryset = queryset.objects.filter(id__in=ids)
    for items in utils.split_every(queryset, 250):
        items = {item.id: item for item in items}
        results = utils.templated_wikidata_query('wikidata/query/labels.rq', {'ids': sorted(items)})
        for id, rows in itertools.groupby(results['results']['bindings'],
                                            key=lambda row: row['id']['value']):
            id = utils.item_uri_to_id(id)
            rows = list(rows)
            items[id].labels = {row['label']['xml:lang']: row['label']['value']
                                for row in rows}
            items[id].save()

