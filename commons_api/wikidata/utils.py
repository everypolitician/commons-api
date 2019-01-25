from typing import Mapping

import re
import SPARQLWrapper
from django.conf import settings
from django.template.loader import get_template
from django.utils import translation

from . import models
from .namespaces import WD, WDS


def lang_dict(terms):
    return {term.language: str(term) for term in terms}

ITEM_URI_RE = re.compile('^' + re.escape(WD) + 'Q[1-9][0-9]*$')
STATEMENT_URI_RE = re.compile('^' + re.escape(WDS) + '[qQ][0-9A-Fa-f-]+$')
DATE_RE = re.compile('^[0-9]{4}-[01][0-9]-[0-3][0-9]$')

def item_uri_to_id(uri):
    if isinstance(uri, dict):
        uri = uri['value']
    if not ITEM_URI_RE.match(uri):
        raise ValueError("Not a Wikidata item URI: {!r}".format(uri))
    return uri[len(WD):]


def get_date(dt):
    if not dt:
        return None
    if isinstance(dt, dict):
        dt = dt['value']
    if not isinstance(dt, str):
        return None
    dt = dt[:10]
    if DATE_RE.match(dt):
        return dt


def statement_uri_to_id(uri):
    if isinstance(uri, dict):
        uri = uri['value']
    if not STATEMENT_URI_RE.match(uri):
        raise ValueError("Not a Wikidata statement URI: {!r}".format(uri))
    return uri[len(WDS):].upper()


def select_multilingual(data: Mapping[str,object],
                        default=None):
    """Selects a value from data based on user's language

    `data` should be keyed with language code `str`s. This function first tries the user's proferred language, falling
    back to `settings.DEFAULT_LANGUAGE` and then "en". If no appropriate value is found in `data`, `default` is
    returned."""
    languages_to_try = (translation.get_language(),
                        getattr(settings, 'DEFAULT_LANGUAGE', 'en'),
                        'en')
    for language in languages_to_try:
        try:
            return data[language]
        except KeyError:
            continue
    return default


def templated_wikidata_query(query_name, context):
    sparql = SPARQLWrapper.SPARQLWrapper(settings.WDQS_URL)
    sparql.setMethod(SPARQLWrapper.POST)
    sparql.setQuery(get_template(query_name).render(context))
    sparql.setReturnFormat(SPARQLWrapper.JSON)
    return sparql.query().convert()
