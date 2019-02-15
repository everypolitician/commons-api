import logging
import time

import celery.app
import celery.task
import functools
import http.client
import itertools
import urllib.error
from typing import Callable, Mapping

import re
import SPARQLWrapper
from django.conf import settings
from django.dispatch import Signal
from django.template.loader import get_template
from django.utils import translation

from .namespaces import WD, WDS


logger = logging.getLogger(__name__)


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


def split_every(it, n):
    """Splits an iterable into sub-iterators each of maximum length n

    Each returned iterator needs consuming before the main iterator is
    iterated over again, otherwise the returned groups will be shorter
    than expected, or returned items returned out of order.
    """
    def group(first):
        yield first
        yield from itertools.islice(it, n-1)
    it = iter(it)
    while True:
        try:
            first = next(it)
        except StopIteration:
            break
        yield group(first)


wdqs_rate_limiting = Signal(['retry_after'])


def templated_wikidata_query(query_name: str, context: dict,
                             rate_limiting_handler: Callable[[bool], None]=None) -> dict:
    """Constructs a query for Wikidata using django.template and returns the parsed results

    If the query elicits a `429 Too Many Requests` response, it retries up to `settings.WDQS_RETRIES` times, and
    calls the rate_limiting_handler callback if provided to signal the start and end of a "stop querying" period.

    :param query_name: A template name that can be loaded by Django's templating system
    :param context: A template context dict to use when rendering the query
    :param rate_limiting_handler: A function to handle rate-limiting requests. Should suspend all querying if called
        with `True`, and resume it if called with `False`.
    :returns: The parsed SRJ results as a basic Python data structure
    """

    rate_limiting_handler = rate_limiting_handler or (lambda suspend: None)
    sparql = SPARQLWrapper.SPARQLWrapper(settings.WDQS_URL)
    sparql.setMethod(SPARQLWrapper.POST)
    sparql.setQuery(get_template(query_name).render(context))
    sparql.setReturnFormat(SPARQLWrapper.JSON)
    has_suspended = False
    try:
        for i in range(1, settings.WDQS_RETRIES + 1):
            try:
                logger.info("Performing query %r (attempt %d/%d)", query_name, i, settings.WDQS_RETRIES)
                response = sparql.query()
            except urllib.error.HTTPError as e:
                if e.code == http.client.TOO_MANY_REQUESTS and i < settings.WDQS_RETRIES:
                    if not has_suspended:
                        has_suspended = True
                        rate_limiting_handler(True)
                    retry_after = int(e.headers.get('Retry-After', 60))
                    time.sleep(retry_after)
                else:
                    raise
            else:
                return response.convert()
    finally:
        if has_suspended:
            rate_limiting_handler(False)


def queries_wikidata(task_func):
    """Decorator for task functions that query Wikidata

    This decorator passes a handle_ratelimiting argument to the wrapped task that should be passed to
    `templated_wikidata_query` to handle rate-limiting requests from WDQS by suspending the execution of tasks that
    query Wikidata. This is achieved by having celery cancel consumption of the given queue by the worker if `suspend`
    is True, and resume it otherwise.

    This behaviour doesn't occur if the task was called directly — i.e. not in a worker.

    Tasks that query Wikidata should be separated from other tasks by being sent to a different queue, by e.g.

    @celery.shared_task(bind=True, queue='wdqs')
    @utils.queries_wikidata
    def task_function(self, …, templated_wikidata_query=None):
        …
    """
    @functools.wraps(task_func)
    def new_task_func(self: celery.task.Task, *args, **kwargs):
        def handle_ratelimiting(suspend):
            app = self.app
            # Celery routes to the right queue using the default exchange and a routing key, so the routing key tells
            # us our queue name. See <https://www.rabbitmq.com/tutorials/amqp-concepts.html#exchange-default>.
            queue = self.request.delivery_info['routing_key']
            # This identifies the current celery worker
            nodename = self.request.hostname
            with app.connection_or_acquire() as conn:
                if suspend:
                    logger.info("WDQS rate-limiting started; WDQS task consumption suspended")
                    app.control.cancel_consumer(queue, connection=conn, destination=[nodename])
                    self.update_state(state='RATE_LIMITED')
                else:
                    logger.info("WDQS rate-limiting finished; WDQS task consumption resumed")
                    app.control.add_consumer(queue, connection=conn, destination=[nodename])
                    self.update_state(state='ACTIVE')

        # Only use a handler if executing in a celery worker.
        rate_limiting_handler = handle_ratelimiting if not self.request.called_directly else None

        return task_func(self,  *args, rate_limiting_handler=rate_limiting_handler, **kwargs)

    return new_task_func
