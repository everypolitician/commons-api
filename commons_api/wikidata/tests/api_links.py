from django.test import TestCase
from django.utils import timezone
from django.views import View

from commons_api.wikidata.views import APILinksMixin
from .. import models


class APILinksTestCase(TestCase):
    maxDiff = None

    def testListViewContext(self):
        response = self.client.get('/country')
        self.assertEqual([{
            'name': 'countries',
            'urls': [{
                'format': 'json',
                'name': 'JSON',
                'url': '/api/country/?format=json',
            }, {
                'format': 'api',
                'name': 'Browsable API',
                'url': '/api/country/?format=api',
            }, {
                'format': 'geojson',
                'name': 'GeoJSON',
                'url': '/api/country/?format=geojson',
            }],
        }], response.context['api_urls'])

    def testDetailViewContext(self):
        models.Country.objects.create(id='Q1',
                                      refresh_labels_last_queued=timezone.now(),
                                      refresh_legislatures_last_queued=timezone.now())
        response = self.client.get('/country/Q1')
        self.assertEqual([{
            'name': 'country',
            'urls': [{
                'format': 'json',
                'name': 'JSON',
                'url': '/api/country/Q1/?format=json',
            }, {
                'format': 'api',
                'name': 'Browsable API',
                'url': '/api/country/Q1/?format=api',
            }, {
                'format': 'geojson',
                'name': 'GeoJSON',
                'url': '/api/country/Q1/?format=geojson',
            }],
        }, {
            'name': 'legislative houses',
            'urls': [{
                'format': 'json',
                'name': 'JSON',
                'url': '/api/legislative-house/?country=Q1&format=json',
            }, {
                'format': 'api',
                'name': 'Browsable API',
                'url': '/api/legislative-house/?country=Q1&format=api',
            }],
        }], response.context['api_urls'])

    def testNonObjectViewNotImplemented(self):
        # Views that aren't subclassed from ListView or DetailView need to implement their own
        # `get_api_base_urls`
        class SomeView(APILinksMixin, View):
            pass

        view = SomeView()
        with self.assertRaises(NotImplementedError):
            view.get_api_base_urls()
        with self.assertRaises(NotImplementedError):
            view.get_context_data()
