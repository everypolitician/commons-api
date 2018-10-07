import celery
import collections
import itertools
from SPARQLWrapper import SPARQLWrapper, JSON
from django.conf import settings
from django.template.loader import get_template

from commons_api.wikidata.utils import item_uri_to_id, statement_uri_to_id, get_date
from .. import models


@celery.shared_task
def refresh_legislature_list(country_id):
    country = models.Country.objects.get(id=country_id)
    sparql = SPARQLWrapper(settings.WDQS_URL)
    sparql.setQuery(get_template('wikidata/query/legislature_list.rq').render({'country': country}))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    # print(get_template('wikidata/query/legislature_list.rq').render())
    # print(len(results['results']['bindings']))
    legislature_positions = collections.defaultdict(list)
    legislative_terms = collections.defaultdict(list)
    for result in results['results']['bindings']:
        administrative_area = models.AdministrativeArea.objects.for_id_and_label(item_uri_to_id(result['adminArea']),
                                                                                 result['adminAreaLabel']['value'])
        administrative_area.save()
        legislature = models.LegislativeHouse.objects.for_id_and_label(item_uri_to_id(result['legislature']),
                                                                       result['legislatureLabel']['value'])
        legislature.administrative_area = administrative_area
        legislature.country = country
        legislature.save()
        if 'legislaturePostLabel' in result:
            position = models.Position.objects.for_id_and_label(item_uri_to_id(result['legislaturePost']),
                                                                result['legislaturePostLabel']['value'])
            position.save()
            legislature_positions[legislature.id].append(position)

    for legislature in models.LegislativeHouse.objects.filter(id__in=legislature_positions):
        legislature.positions.set(legislature_positions[legislature.id])

    house_positions = [{'house': legislature_id, 'position': position.id}
                       for legislature_id, positions in legislature_positions.items()
                       for position in positions]
    sparql.setQuery(get_template('wikidata/query/legislature_terms_list.rq').render({'house_positions': house_positions}))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    # print(house_positions)
    # print(get_template('wikidata/query/legislature_terms_list.rq').render())
    # print(len(results['results']['bindings']))
    for result in results['results']['bindings']:
        if 'termSpecificPositionLabel' in result:
            term_specific_position = models.Position.objects.for_id_and_label(
                item_uri_to_id(result['termSpecificPosition']),
                result['termSpecificPositionLabel']['value'])
            term_specific_position.save()
        else:
            term_specific_position = None
        legislative_term = models.LegislativeTerm.objects.for_id_and_label(item_uri_to_id(result['term']),
                                                                           result['termLabel']['value'])
        legislative_term.start = get_date(result.get('termStart'))
        legislative_term.end = get_date(result.get('termEnd'))
        legislative_term.save()
        legislative_terms[item_uri_to_id(result['house'])].append(legislative_term)

        try:
            lht = models.LegislativeHouseTerm.objects.get(legislative_house_id=item_uri_to_id(result['house']),
                                                          legislative_term_id=item_uri_to_id(result['term']))
        except models.LegislativeHouseTerm.DoesNotExist:
            lht = models.LegislativeHouseTerm(legislative_house_id=item_uri_to_id(result['house']),
                                              legislative_term_id=item_uri_to_id(result['term']))
        lht.term_specific_position = term_specific_position
        lht.save()

@celery.shared_task
def refresh_legislature_members(legislature_id):
    house = models.LegislativeHouse.objects.get(id=legislature_id)
    sparql = SPARQLWrapper(settings.WDQS_URL)
    sparql.setQuery(get_template('wikidata/query/legislature_memberships.rq').render({'positions': house.positions.all()}))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    seen_statement_ids = set()
    for i, (statement, rows) in enumerate(itertools.groupby(results['results']['bindings'], key=lambda row: row['statement']['value'])):
        rows = list(rows)
        statement_id = statement_uri_to_id(statement)
        seen_statement_ids.add(statement_id)
        first_row = rows[0]
        person = models.Person.objects.for_id_and_label(item_uri_to_id(first_row['person']),
                                                        first_row['personLabel']['value'])
        person.save()
        print("{:6} {:10} {}".format(i, item_uri_to_id(first_row['person']), first_row['personLabel']['value']))

        if 'districtLabel' in first_row:
            district = models.ElectoralDistrict.objects.for_id_and_label(item_uri_to_id(first_row['district']),
                                                                         first_row['districtLabel']['value'],
                                                                         save=True)
        else:
            district = None
        if first_row.get('endCauseLabel', {}).get('type') == 'uri':
            end_cause = models.Term.objects.for_id_and_label(item_uri_to_id(first_row['endCause']),
                                                             first_row['endCauseLabel']['value'],
                                                             save=True)
        else:
            end_cause = None
        if 'subjectHasRoleLabel' in first_row:
            subject_has_role = models.Term.objects.for_id_and_label(item_uri_to_id(first_row['subjectHasRole']),
                                                                    first_row['subjectHasRoleLabel']['value'],
                                                                    save=True)
        else:
            subject_has_role = None

        legislative_terms = []
        for row in rows:
            if 'termLabel' in row:
                legislative_term = models.LegislativeTerm.objects.for_id_and_label(item_uri_to_id(row['term']),
                                                                                   row['termLabel']['value'])
                legislative_term.start = get_date(row.get('termStart'))
                legislative_term.end = get_date(row.get('termEnd'))
                legislative_term.save()
                legislative_terms.append(legislative_term)

        try:
            membership = models.LegislativeMembership.objects.get(id=statement_id)
        except models.LegislativeMembership.DoesNotExist:
            membership = models.LegislativeMembership(id=statement_id)
        membership.person = person
        membership.district = district
        membership.legislative_house = house
        membership.subject_has_role = subject_has_role
        membership.end_cause = end_cause
        membership.start = get_date(first_row.get('start'))
        membership.end = get_date(first_row.get('end'))
        if not membership.start:
            try:
                membership.start = min(term.start for term in legislative_terms if term.start)
            except ValueError:
                pass
        if not membership.end:
            try:
                membership.end = min(term.end for term in legislative_terms if term.end)
            except ValueError:
                pass
        membership.save()
        membership.legislative_terms.set(legislative_terms)

    models.LegislativeMembership.objects.filter(legislative_house=house).exclude(id__in=seen_statement_ids).delete()
