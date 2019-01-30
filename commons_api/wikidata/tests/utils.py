import unittest.mock

from SPARQLWrapper import JSON, POST
from django.test import TestCase

from commons_api.wikidata import utils


class SparqlTestCase(TestCase):
    @unittest.mock.patch('SPARQLWrapper.SPARQLWrapper')
    def test_templated_wikidata_query(self, SPARQLWrapper):
        sparql_wrapper = unittest.mock.Mock()
        sparql_results = unittest.mock.Mock()
        sparql_data = unittest.mock.Mock()
        SPARQLWrapper.return_value = sparql_wrapper
        sparql_wrapper.query.return_value = sparql_results
        sparql_results.convert.return_value = sparql_data

        result = utils.templated_wikidata_query('wikidata/query/country_list.rq', {})

        sparql_wrapper.setMethod.assert_called_once_with(POST)
        sparql_wrapper.setReturnFormat.assert_called_once_with(JSON)

        self.assertEqual(sparql_data, result)


class SplitEveryTestCase(TestCase):
    def testSplitsList(self):
        data = list(range(10))
        result = utils.split_every(data, 3)
        result = [list(group) for group in result]
        self.assertEqual([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]], result)