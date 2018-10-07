import celery
from SPARQLWrapper import SPARQLWrapper, JSON
from django.conf import settings
from django.template.loader import get_template

from commons_api.wikidata.utils import item_uri_to_id
from commons_api.wikidata import models


__all__ = ['refresh_country_list']


@celery.shared_task
def refresh_country_list():
    sparql = SPARQLWrapper(settings.WDQS_URL)
    sparql.setQuery(get_template('wikidata/query/country_list.rq').render())
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    seen_ids = set()
    for result in results['results']['bindings']:
        id = item_uri_to_id(result['item'])
        country = models.Country.objects.for_id_and_label(id, str(result['itemLabel']['value']))
        country.save()
        seen_ids.add(id)
    for country in models.Country.objects.exclude(id__in=seen_ids):
        country.delete()
