import celery
import itertools
import rdflib
from django.contrib.contenttypes.models import ContentType
import requests

from commons_api.wikidata import models
from commons_api.wikidata.utils import templated_wikidata_query, item_uri_to_id

__all__ = ['refresh_from_entity_data', 'refresh_labels']


def get_wikidata_model(app_label, model):
    ct = ContentType.objects.get_by_natural_key(app_label, model)
    model = ct.model_class()
    if not issubclass(model, models.WikidataItem):
        raise TypeError('Model {} with content_type {}.{} is not a WikidataItem'.format(model, app_label, model))
    return model


@celery.shared_task
def refresh_from_entity_data(app_label, model, id):
    model = get_wikidata_model(app_label, model)
    obj = model.objects.get(id=id)  # type: models.WikidataItem
    response = requests.get('https://www.wikidata.org/wiki/Special:EntityData/{}.rdf'.format(id))
    graph = rdflib.ConjunctiveGraph()
    graph.parse(data=response.text, format='xml')
    obj.update_from_entity_data(graph)
    obj.save()


@celery.shared_task
def refresh_labels(app_label, model, ids=None):
    model = get_wikidata_model(app_label, model)
    if ids is None:
        ids = model.objects.all().values_list('id', flat=True)
    for i in range(0, len(ids), 250):
        ids_for_query = ids[i:i+250]
        items = {item.id: item for item in model.objects.filter(id__in=ids_for_query)}
        results = templated_wikidata_query('wikidata/query/labels.rq', {'ids': ids_for_query})
        for id, rows in itertools.groupby(results['results']['bindings'],
                                            key=lambda row: row['id']['value']):
            id = item_uri_to_id(id)
            rows = list(rows)
            print(rows)
            items[id].labels = {row['label']['xml:lang']: row['label']['value']
                                for row in rows}
            items[id].save()
