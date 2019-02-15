Architecture
============


Data ingest
-----------

Data are pulled in with a number of celery tasks, listed at :ref:`wikidata-tasks`.


Boundaries
----------

``commons-api`` embeds `represent-boundaries <https://represent.poplus.org/>`_ for storing boundary data.
Boundaries are pulled in using celery tasks from two sources:

* ``boundaries/`` directories in proto-commons repositories
* GeoShapes (linked with ``wdt:P3896`` properties in Wikidata) from Wikimedia Commons

Represent Boundaries has two models, :py:class:`boundaries.models.BoundarySet` and
:py:class:`boundaries.models.Boundary`. For boundaries sourced from proto-commons repositories, each shapefile is
mapped to its own ``BoundarySet``. Commons geoshapes have a :py:class:`boundaries.models.BoundarySet` per source URL,
and so have a single :py:class:`boundaries.models.Boundary` per :py:class:`boundaries.models.BoundarySet`.

The represent-boundaries views are included in :py:data:`commons_api.urls.urlpatterns` at ``/boundary-sets/`` and
``/boundaries/``.


Models
------

Models representing Wikidata items all subclass :py:class:`commons_api.wikidata.models.WikidataItem`, which implements
common functionality around labels, links to Wikipedia, etc. Wikidata IDs are used as primary keys.

Some models are timebound, i.e. they potentially have start/inception and end/dissolution dates in Wikidata. These
subclass :py:class:`commons_api.wikidata.models.Timebound`.

Some Wikidata IDs will have representations in different models, e.g. Andorra is both a
:py:class:`commons_api.wikidata.models.Country` and an :py:class:`commons_api.wikidata.models.AdministrativeArea` for
its national legislature.

Memberships correspond to statements — not items — in Wikidata, so
:py:class:`commons_api.wikidata.models.LegislativeMembership` doesn't subclass
:py:class:`commons_api.wikidata.models.WikidataItem`.


API
---

``commons-api`` has an API built on top of django-rest-framework and exposed at ``/api/``. The API is a standard use
of django-rest-framework, split across:

* :py:mod:`commons_api.wikidata.api` (the :py:class:`rest_framework.routers.DefaultRouter` definition, where viewsets
  get wired in)
* :py:mod:`commons_api.wikidata.viewsets` (these handle the list and detail views for API objects, using serializers
  and renderers)
* :py:mod:`commons_api.wikidata.serializers` (these extract data from ORM objects into a simple Python data structure)
* :py:mod:`commons_api.wikidata.renderers` (these turn the simple Python data structure into representations (e.g.
  JSON, CSV) to send to clients.
