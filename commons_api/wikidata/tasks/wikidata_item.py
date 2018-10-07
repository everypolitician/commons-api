import celery
import rdflib
from django.contrib.contenttypes.models import ContentType
import requests

from commons_api.wikidata import models

__all__ = ['refresh_from_entity_data']


@celery.shared_task
def refresh_from_entity_data(app_label, model, id):
    ct = ContentType.objects.get_by_natural_key(app_label, model)
    model = ct.model_class()
    if not issubclass(model, models.WikidataItem):
        raise TypeError('Model {} with content_type {}.{} is not a WikidataItem'.format(model, app_label, model))
    obj = model.objects.get(id=id)  # type: models.WikidataItem
    response = requests.get('https://www.wikidata.org/wiki/Special:EntityData/{}.rdf'.format(id))
    graph = rdflib.ConjunctiveGraph()
    graph.parse(data=response.text, format='xml')
    obj.update_from_entity_data(graph)
    obj.save()
