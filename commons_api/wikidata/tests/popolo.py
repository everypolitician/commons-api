import json

from django.test import TestCase

from .. import renderers

class PopoloJSONRendererTestCase(TestCase):
    empty_house = {
        'id': 'Q11005',
        'labels': {
            'en': 'House of Commons',
        },
        'districts': [],
        'memberships': [],
    }

    def setUp(self):
        self.renderer = renderers.PopoloJSONRenderer()

    def testRenderEmptyLegislativeHouse(self):
        rendered_data = json.loads(self.renderer.render(self.empty_house, None, None).decode())
        self.assertEqual([], rendered_data.get('areas'))
        self.assertEqual([], rendered_data.get('persons'))
        self.assertEqual([], rendered_data.get('memberships'))
        self.assertEqual([self.renderer.organization_to_popolo(self.empty_house, classification='branch')],
                         rendered_data.get('organizations'))
