import json

from rest_framework.renderers import BaseRenderer

from . import models
from .namespaces import WDS


class PopoloJSONRenderer(BaseRenderer):
    media_type = 'application/popolo+json'
    format = 'popolo-json'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        results = data['results']
        persons, organizations, areas, memberships = {}, {}, {}, []
        for membership in results:  # type: models.LegislativeMembership
            if membership['person']['id'] not in persons:
                links = []
                if membership['person']['facebook_id']:
                    links.append({
                        'note': 'facebook',
                        'url': 'https://www.facebook.com/' + membership['person']['facebook_id']
                    })
                if membership['person']['twitter_id']:
                    links.append({
                        'note': 'twitter',
                        'url': 'https://twitter.com/' + membership['person']['twitter_id']
                    })
                persons[membership['person']['id']] = {
                    'id': membership['person']['id'],
                    'name': {'lang:{}'.format(k): v
                             for k, v in membership['person']['labels'].items() if k in ('en', 'cy')},
                    'identifiers': [{
                        'scheme': 'wikidata',
                        'identifier': membership['person']['id'],
                    }],
                    'links': links,
                }
            if membership['district'] and membership['district']['id'] not in areas:
                areas[membership['district']['id']] = {
                    'id': membership['district']['id'],
                    'name': {'lang:{}'.format(k): v
                             for k, v in membership['district']['labels'].items() if k in ('en', 'cy')},
                }
            if membership['legislative_house']['id'] not in areas:
                organizations[membership['legislative_house']['id']] = {
                    'id': membership['legislative_house']['id'],
                    'name': {'lang:{}'.format(k): v
                             for k, v in membership['legislative_house']['labels'].items() if k in ('en', 'cy')},
                    'classification': 'branch',
                    'area_id': membership['legislative_house']['administrative_area']['id'],
                }
            memberships.append({
                'id': str(WDS[membership['id']]),
                'person_id': membership['person']['id'],
                'organization_id': membership['legislative_house_id'],
                'area_id': membership['district_id'],
                'start_date': membership['start'],
                'end_date': membership['end'],
            })
        return json.dumps({
            'persons': sorted(persons.values(), key=lambda person: person['id']),
            'organizations': sorted(organizations.values(), key=lambda organization: organization['id']),
            'areas': sorted(areas.values(), key=lambda area: area['id']),
            'memberships': memberships,
        }, indent=2)