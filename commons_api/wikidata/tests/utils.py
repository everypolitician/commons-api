import unittest.mock

from SPARQLWrapper import JSON, POST
from django.test import TestCase

from commons_api.wikidata.utils import templated_wikidata_query


class SparqlTestCase(TestCase):
    @unittest.mock.patch('SPARQLWrapper.SPARQLWrapper')
    def test_templated_wikidata_query(self, SPARQLWrapper):
        sparql_wrapper = unittest.mock.Mock()
        sparql_results = unittest.mock.Mock()
        sparql_data = unittest.mock.Mock()
        SPARQLWrapper.return_value = sparql_wrapper
        sparql_wrapper.query.return_value = sparql_results
        sparql_results.convert.return_value = sparql_data

        result = templated_wikidata_query('wikidata/query/country_list.rq', {})

        sparql_wrapper.setMethod.assert_called_once_with(POST)
        sparql_wrapper.setReturnFormat.assert_called_once_with(JSON)

        self.assertEqual(sparql_data, result)
