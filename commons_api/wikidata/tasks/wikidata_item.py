import datetime

import celery
import itertools
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from commons_api.wikidata import models, utils

__all__ = ['refresh_labels']


def get_wikidata_model(app_label, model):
    ct = ContentType.objects.get_by_natural_key(app_label, model)
    model = ct.model_class()
    if not issubclass(model, models.WikidataItem):
        raise TypeError('Model {} with content_type {}.{} is not a WikidataItem'.format(model, app_label, model))
    return model


@celery.shared_task
def refresh_labels(app_label, model, ids=None, queued_at=None):
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


@celery.shared_task
def refresh_all_labels(not_queued_in=datetime.timedelta(7)):
    queued_at = timezone.now()
    last_queued_threshold = queued_at - not_queued_in

    for model in apps.get_models():
        if issubclass(model, models.WikidataItem):
            queryset = model.objects.filter(Q(labels_last_queued__lt=last_queued_threshold) |
                                            Q(labels_last_queued__isnull=True))
            if queryset.update(labels_last_queued=queued_at) > 0:
                ct = ContentType.objects.get_for_model(model)
                refresh_labels.delay(ct.app_label, ct.model, queued_at=queued_at)
