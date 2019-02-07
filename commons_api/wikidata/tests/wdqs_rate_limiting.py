import http.client
import uuid
from unittest import mock
from urllib.error import HTTPError

from celery.app.task import Context
from django.conf import settings
from django.test import TestCase

from commons_api import celery_app
from commons_api.wikidata.tasks import refresh_country_list


class WDQSRateLimitingTestCase(TestCase):
    @mock.patch('SPARQLWrapper.Wrapper.urlopener')
    @mock.patch('time.sleep')
    def testRetriesIfTooManyRequests(self, time_sleep, urlopen):
        retry_after = 10
        urlopen.side_effect = HTTPError(url=None,
                                        code=http.client.TOO_MANY_REQUESTS,
                                        hdrs={'Retry-After': str(retry_after)},
                                        msg='', fp=None)
        with self.assertRaises(HTTPError):
            refresh_country_list()

        self.assertEqual(settings.WDQS_RETRIES, urlopen.call_count)
        self.assertEqual(settings.WDQS_RETRIES - 1, time_sleep.call_count)
        time_sleep.assert_has_calls([mock.call(retry_after)] * (settings.WDQS_RETRIES - 1))

    @mock.patch('SPARQLWrapper.Wrapper.urlopener')
    @mock.patch('time.sleep')
    def testSuspendsConsuming(self, time_sleep, urlopen):
        retry_after = 10
        urlopen.side_effect = HTTPError(url=None,
                                        code=http.client.TOO_MANY_REQUESTS,
                                        hdrs={'Retry-After': str(retry_after)},
                                        msg='', fp=None)
        refresh_country_list._default_request = Context(id=str(uuid.uuid4()),
                                                        called_directly=False,
                                                        delivery_info={'routing_key': 'wdqs'},
                                                        hostname='nodename')

        with mock.patch.object(celery_app.control, 'cancel_consumer') as cancel_consumer, \
                mock.patch.object(celery_app.control, 'add_consumer') as add_consumer:
            manager = mock.Mock()
            manager.attach_mock(cancel_consumer, 'cancel_consumer')
            manager.attach_mock(add_consumer, 'add_consumer')
            manager.attach_mock(time_sleep, 'sleep')
            with self.assertRaises(HTTPError):
                refresh_country_list.run()
            manager.assert_has_calls([mock.call.cancel_consumer('wdqs', connection=mock.ANY, destination=['nodename']),
                                      mock.call.sleep(retry_after),
                                      mock.call.sleep(retry_after),
                                      mock.call.sleep(retry_after),
                                      mock.call.sleep(retry_after),
                                      mock.call.add_consumer('wdqs', connection=mock.ANY, destination=['nodename'])])
