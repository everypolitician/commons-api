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


class WikipediaArticlesTestCase(TestCase):
    @unittest.mock.patch.object(legislature.refresh_legislatures, 'delay')
    @unittest.mock.patch('commons_api.wikidata.utils.templated_wikidata_query')
    def testRefreshWikipediaArticles(self, templated_wikidata_query, refresh_legislatures_delay):
        templated_wikidata_query.return_value = {
            'results': {'bindings': [{
                'id': {'value': namespaces.WD['Q16']},
                'name': {'value': 'Canada', 'xml:lang': 'en'},
                'article': {'value': 'https://en.wikipedia.org/wiki/Canada'},
            }, {
                'id': {'value': namespaces.WD['Q16']},
                'name': {'value': 'Canadá', 'xml:lang': 'es'},
                'article': {'value': 'https://es.wikipedia.org/wiki/Canad%C3%A1'},
            }, {
                'id': {'value': namespaces.WD['Q145']},
                'name': {'value': 'Reino Unido', 'xml:lang': 'es'},
                'article': {'value': 'https://es.wikipedia.org/wiki/Reino_Unido'},
            }]}
        }
        queued_at = timezone.now()
        countries = {
            'ca': models.Country.objects.create(id='Q16',
                                                refresh_wikipedia_articles_last_queued=queued_at),
            'gb': models.Country.objects.create(id='Q145',
                                                refresh_wikipedia_articles_last_queued=queued_at),
        }
        wikidata_item.refresh_wikipedia_articles('wikidata', 'country', queued_at=queued_at)
        for country in countries.values():
            country.refresh_from_db()

        self.assertEqual({'en': 'Canada', 'es': 'Canadá'}, countries['ca'].wikipedia_article_titles)
        self.assertEqual({'es': 'Reino Unido'}, countries['gb'].wikipedia_article_titles)

        self.assertEqual({'en': 'https://en.wikipedia.org/wiki/Canada',
                          'es': 'https://es.wikipedia.org/wiki/Canad%C3%A1'},
                         countries['ca'].wikipedia_article_links)
        self.assertEqual({'es': 'https://es.wikipedia.org/wiki/Reino_Unido'},
                         countries['gb'].wikipedia_article_links)
