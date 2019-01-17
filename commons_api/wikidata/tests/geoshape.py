import datetime
import http.client
import unittest.mock

import pytz
from boundaries.models import Boundary
from django.test import TestCase
from django.utils import timezone

from .. import models, tasks
from ... import celery_app


@unittest.mock.patch.object(celery_app, 'send_task', lambda *args, **kwargs: None)
class RefreshGeoshapeTestCase(TestCase):
    def setUp(self):
        self.example_geoshape = {
            'license': 'CC0-1.0',
            'sources': 'sources',
            'data': {
                'type': 'FeatureCollection',
                'features': [{
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
                    }
                }]
            }
        }

    def testHandlesMissingGeoshapeURL(self):
        country = models.Country.objects.create(id='Q142')
        country.refresh_from_db()
        result = tasks.refresh_geoshape('wikidata', 'country', country.id,
                                        country.refresh_geoshape_last_queued)
        self.assertEqual({'result': 'unnecessary'}, result)

    def testHandlesSinceRequeued(self):
        queued_at = timezone.now()
        country = models.Country.objects.create(id='Q142',
                                                refresh_geoshape_last_queued=queued_at + datetime.timedelta(1))
        result = tasks.refresh_geoshape('wikidata', 'country', country.id, queued_at)
        self.assertEqual({'result': 'since_requeued'}, result)

    @unittest.mock.patch('requests.get')
    def testHandlesWithGeoshapeURL(self, requests_get):
        queued_at = timezone.now()
        geoshape_url = 'http://example.org/some/geoshape.map'
        country = models.Country.objects.create(id='Q142',
                                                refresh_geoshape_last_queued=queued_at,
                                                geoshape_url=geoshape_url)
        response = unittest.mock.Mock()
        response.headers = {
            'Last-Modified': 'Fri, 25 May 2018 14:44:24 GMT',
        }
        response.json.return_value = self.example_geoshape
        requests_get.return_value = response
        result = tasks.refresh_geoshape('wikidata', 'country', country.id, queued_at)
        self.assertEqual({'result': 'refreshed'}, result)

        country.refresh_from_db()
        self.assertEqual(datetime.datetime(2018, 5, 25, 14, 44, 24, tzinfo=pytz.utc), country.geoshape_last_modified)

        boundary = Boundary.objects.get(external_id=country.id)
        self.assertEqual(boundary.id, country.boundary_id)

    @unittest.mock.patch('requests.get')
    def testWithLastModified(self, requests_get):
        queued_at = datetime.datetime(2018, 5, 25, 14, 44, 24, tzinfo=pytz.utc)
        geoshape_url = 'http://example.org/some/geoshape.map'
        country = models.Country.objects.create(id='Q142',
                                                refresh_geoshape_last_queued=queued_at,
                                                geoshape_last_modified=queued_at,
                                                geoshape_url=geoshape_url)
        response = unittest.mock.Mock()
        response.status_code = http.client.NOT_MODIFIED
        response.json.return_value = self.example_geoshape
        requests_get.return_value = response
        result = tasks.refresh_geoshape('wikidata', 'country', country.id, queued_at)
        self.assertEqual({'result': 'not_modified'}, result)
        requests_get.called_once_with(geoshape_url, headers={'If-Modified-Since': 'Fri, 25 May 2018 14:44:24 GMT'})
        # Has done nothing, because it assumes a current boundary is up to date
        self.assertEqual(0, Boundary.objects.count())
