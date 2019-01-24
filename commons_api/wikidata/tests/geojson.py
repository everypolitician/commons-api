import json

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import Point
from django.test import TestCase

from .. import renderers


class GeoJSONRendererTestCase(TestCase):
    def setUp(self):
        self.renderer = renderers.GeoJSONRenderer()
        self.data_gb = {
            "id": "Q145",
            "labels": {
                "en": "United Kingdom"
            },
            "flag_image": None,
            "population": 65102385,
            "iso_3166_1_code": "GB",
            "wikipedia_articles": {},
            "geometry": {
                "type": "Point",
                "coordinates": [
                    -2.882623571004757,
                    54.1551889188512
                ]
            }
        }

    def testRendersCountry(self):
        rendered_data = self.renderer.render(self.data_gb, None, None).decode()
        data_source = DataSource(rendered_data)
        feature = data_source[0][0]
        # Check the geometry round-tripped
        self.assertEqual(self.data_gb['geometry'], json.loads(feature.geom.geojson))
        # There should be fields for everything but 'geometry'
        self.assertEqual(set(self.data_gb) - {'geometry'},
                         set(feature.fields))
        self.assertEqual(self.data_gb['id'], str(feature['id']))
        self.assertEqual(self.data_gb['labels'], json.loads(str(feature['labels'])))

    def testRendersList(self):
        data = {
            'results': [self.data_gb, self.data_gb],
        }
        rendered_data = self.renderer.render(data, None, None).decode()
        data_source = DataSource(rendered_data)
        # There are two features in this feature collection
        self.assertEqual(2, len(data_source[0]))
