import collections
import json

from rest_framework.renderers import BaseRenderer, JSONRenderer

from . import models
from .namespaces import WDS


class GeoJSONRenderer(JSONRenderer):
    media_type = 'application/vnd.geo+json'
    format = 'geojson'

    def to_geojson(self, data):
        return {
            'type': 'Feature',
            'properties': {
                k: v for k, v in data.items() if k != 'geometry'
            },
            'geometry': data['geometry'],
        }

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if 'results' in data:
            data = {
                'type': 'FeatureCollection',
                'features': [self.to_geojson(result) for result in data['results']],
            }
        else:
            data = self.to_geojson(data)
        return super().render(data, accepted_media_type, renderer_context)

class PopoloJSONRenderer(JSONRenderer):
    media_type = 'application/popolo+json'
    format = 'popolo-json'

    def to_m17n(self, data):
        return {'lang:{}'.format(k): v
                for k, v in data.items()}

    def organization_to_popolo(self, data, classification=None):
        return {
            'id': data['id'],
            'name': self.to_m17n(data['labels']),
            'classification': classification,
        }

    def person_to_popolo(self, data):
        links = []
        if data['facebook_id']:
            links.append({
                'note': 'facebook',
                'url': 'https://www.facebook.com/' + data['facebook_id']
            })
        if data['twitter_id']:
            links.append({
                'note': 'twitter',
                'url': 'https://twitter.com/' + data['twitter_id']
            })
        return {
            'id': data['id'],
            'name': self.to_m17n(data['labels']),
            'identifiers': [{
                'scheme': 'wikidata',
                'identifier': data['id'],
            }],
            'links': links,
        }

    def membership_to_popolo(self, data):
        return {
            'id': str(WDS[data['id']]),
            'person_id': data['person']['id'],
            'on_behalf_of_id': (data.get('party') or {}).get('id'),
            'parliamentary_group_id': (data.get('parliamentary_group') or {}).get('id'),
            'organization_id': data['id'],
            'role_code': data['position']['id'],
            'role': self.to_m17n(data['position']['labels']),
            'area_id': data['district_id'],
            'start_date': data['start'],
            'end_date': data['end'],
        }

    def render(self, data, accepted_media_type=None, renderer_context=None):
        persons, organizations, memberships = {}, {}, []
        organizations[data['id']] = self.organization_to_popolo(data, classification='branch')

        for membership in data['memberships']:  # type: models.LegislativeMembership
            if membership['person']['id'] not in persons:
                persons[membership['person']['id']] = self.person_to_popolo(membership['person'])
            if membership['parliamentary_group'] and membership['parliamentary_group']['id'] not in organizations:
                organizations[membership['parliamentary_group']['id']] = \
                    self.organization_to_popolo(membership['parliamentary_group'], classification='party')
            if membership['party'] and membership['party']['id'] not in organizations:
                organizations[membership['party']['id']] = \
                    self.organization_to_popolo(membership['party'], classification='party')

            memberships.append(self.membership_to_popolo(membership))
        return super().render({
            'persons': sorted(persons.values(), key=lambda person: person['id']),
            'organizations': sorted(organizations.values(), key=lambda organization: organization['id']),
            'areas': data['districts'],
            'memberships': memberships,
        }, accepted_media_type, renderer_context)


class PopoloGeoJSONRenderer(GeoJSONRenderer):
    media_type = 'application/popolo+vnd.geo+json'
    format = 'popolo-geojson'

    def update_district_with_membership(self, district, membership):
        try:
            district['memberships'] += [membership]
        except KeyError as e:
            district['memberships'] = [membership]

    def render(self, data, accepted_media_type=None, renderer_context=None):
        districts = data['districts']
        districts_by_id = {district['id']: district for district in districts}
        for membership in data['memberships']:
            try:
                self.update_district_with_membership(districts_by_id[membership['district_id']], membership)
            except KeyError:
                pass        # Not all members have districts, not all districts will be in the districts_by_id

        return super().render({'results': list(districts)}, accepted_media_type, renderer_context)
