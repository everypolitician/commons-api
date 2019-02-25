import celery
from commons_api.wikidata import utils
from commons_api.wikidata import models


__all__ = ['refresh_country_list']


@celery.shared_task(bind=True, queue='wdqs')
@utils.queries_wikidata
def refresh_country_list(self, rate_limiting_handler):
    results = utils.templated_wikidata_query('wikidata/query/country_list.rq', {}, rate_limiting_handler)
    seen_ids = set()
    for result in results['results']['bindings']:
        id = utils.item_uri_to_id(result['item'])
        country = models.Country.objects.for_id_and_label(id, str(result['itemLabel']['value']))
        country.iso_3166_1_code = result['itemCode']['value'].upper() if result.get('itemCode') else None
        country.save()
        seen_ids.add(id)
    for country in models.Country.objects.exclude(id__in=seen_ids):
        country.delete()
