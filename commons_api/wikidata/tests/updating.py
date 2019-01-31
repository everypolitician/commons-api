import datetime
import unittest.mock

from django.test import TestCase
from django.utils import timezone

from .. import models, namespaces
from ..tasks import legislature, wikidata_item


class LabelsTestCase(TestCase):
    @unittest.mock.patch.object(legislature.refresh_legislatures, 'delay')
    def setUp(self, refresh_legislatures_delay):
        self.refresh_labels_last_queued = timezone.now() - datetime.timedelta(2)
        self.country = models.Country.objects.create(id='Q142',
                                                     refresh_labels_last_queued=self.refresh_labels_last_queued)

    def testRefreshAllQueuesNew(self):
        models.Country.objects.update(refresh_labels_last_queued=None)
        with unittest.mock.patch.object(wikidata_item.refresh_labels, 'delay') as refresh_delay:
            wikidata_item.refresh_labels.periodic_queuing_task()
        refresh_delay.assert_called_once_with(app_label='wikidata', model='country',
                                              queued_at=unittest.mock.ANY)
        self.country.refresh_from_db()
        self.assertIsNotNone(self.country.refresh_labels_last_queued)

    def testRefreshAllQueuesNotRecentlyQueued(self):
        with unittest.mock.patch.object(wikidata_item.refresh_labels, 'delay') as refresh_delay:
            wikidata_item.refresh_labels.periodic_queuing_task(datetime.timedelta(1))
            refresh_delay.assert_called_once_with(app_label='wikidata', model='country',
                                                  queued_at=unittest.mock.ANY)
        self.country.refresh_from_db()
        self.assertGreater(self.country.refresh_labels_last_queued, self.refresh_labels_last_queued)

    def testRefreshAllDoesntQueueRecentlyQueued(self):
        with unittest.mock.patch.object(wikidata_item.refresh_labels, 'delay') as refresh_labels_delay:
            wikidata_item.refresh_labels.periodic_queuing_task(datetime.timedelta(3))
            refresh_labels_delay.assert_not_called()
        self.country.refresh_from_db()
        self.assertEqual(self.country.refresh_labels_last_queued, self.refresh_labels_last_queued)

    @unittest.mock.patch('commons_api.wikidata.utils.templated_wikidata_query')
    def testRefreshForModelRefreshesMatchingLastQueued(self, templated_wikidata_query):
        templated_wikidata_query.return_value = {
            'results': {'bindings': [{
                'id': {'value': namespaces.WD[self.country.id]},
                'label': {'value': 'France', 'xml:lang': 'en'},
            }, {
                'id': {'value': namespaces.WD[self.country.id]},
                'label': {'value': 'Frankreich', 'xml:lang': 'de'},
            }]}
        }
        wikidata_item.refresh_labels('wikidata', 'country', queued_at=self.refresh_labels_last_queued)
        templated_wikidata_query.assert_called_once_with('wikidata/query/labels.rq', {'ids': [self.country.id]})
        self.country.refresh_from_db()
        self.assertEqual({'en': 'France', 'de': 'Frankreich'}, self.country.labels)
