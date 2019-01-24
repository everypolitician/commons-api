import datetime
import json

from django.contrib.gis.gdal import OGRGeometry, DataSource

from boundaries.models import Feature, BoundarySet, Definition
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .. import models, serializers


class SpatialSerializerTestCase(TestCase):
    def setUp(self):
        self.serializer_class = serializers.CountrySerializer
        self.country = models.Country(id='Q145')
        self.definition = Definition({'name_func': lambda feature: 'name',
                                      'id_func': lambda feature: 'id',
                                      'name': 'test-set'})
        self.boundary_set = BoundarySet.objects.create(slug='test-set',
                                                       last_updated=datetime.datetime.now())
        self.feature = DataSource(json.dumps({
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [
                    [
                        [30, 10], [40, 40], [20, 40], [10, 20], [30, 10],
                    ],
                ],
            },
        }))[0][0]
        self.boundary = Feature(self.feature,
                                boundary_set=self.boundary_set,
                                definition=self.definition).create_boundary()
        self.request_factory = APIRequestFactory()

    def testWithoutGeometry(self):
        serializer_context = {'format': 'json',
                              'request': self.request_factory.get(path='/api/country/Q145')}
        serializer = self.serializer_class(instance=self.country, context=serializer_context)
        self.assertNotIn('geometry', serializer.data)

    def testWithGeoJSONFormatNoGeometry(self):
        serializer_context = {'format': 'geojson',
                              'request': self.request_factory.get(path='/api/country/Q145')}
        serializer = self.serializer_class(instance=self.country, context=serializer_context)
        self.assertEqual(None, serializer.data['geometry'])

    def testWithGeometryParameterNoGeometry(self):
        serializer_context = {'format': 'json',
                              'request': self.request_factory.get(path='/api/country/Q145',
                                                                  data={'geometry': 'centroid'})}
        serializer = self.serializer_class(instance=self.country, context=serializer_context)
        self.assertEqual(None, serializer.data['geometry'])

    def testWithCentroidGeometryParameterAndGeometry(self):
        self.country.boundary_id = self.boundary.id
        serializer_context = {'format': 'json',
                              'request': self.request_factory.get(path='/api/country/Q145',
                                                                  data={'geometry': 'centroid'})}
        serializer = self.serializer_class(instance=self.country, context=serializer_context)
        self.assertEqual(json.loads(self.feature.geom.centroid.geojson), serializer.data['geometry'])

    def testWithShapeGeometryParameterAndGeometry(self):
        self.country.boundary_id = self.boundary.id
        serializer_context = {'format': 'json',
                              'request': self.request_factory.get(path='/api/country/Q145',
                                                                  data={'geometry': 'shape'})}
        serializer = self.serializer_class(instance=self.country, context=serializer_context)
        self.assertIn('coordinates', serializer.data['geometry'])

    def testWithUnknownGeometryParameterAndGeometry(self):
        self.country.boundary_id = self.boundary.id
        serializer_context = {'format': 'json',
                              'request': self.request_factory.get(path='/api/country/Q145',
                                                                  data={'geometry': 'cake'})}
        serializer = self.serializer_class(instance=self.country, context=serializer_context)
        self.assertNotIn('geometry', serializer.data)
