.. commons-api documentation master file, created by
   sphinx-quickstart on Tue Feb 12 12:46:01 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to commons-api's documentation!
=======================================

``commons-api`` provides a view onto democracy data maintained in Wikidata.

It periodically pulls in data using SPARQL queries against the `Wikidata Query Service (WDQS)
<https://query.wikidata.org/>`_, run as `celery <https://docs.celeryproject.org/>`_ tasks. Data are stored using the
Django ORM, and exposed through views and templates, and a `django-rest-framework
<https://www.django-rest-framework.org/>`_ API.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   architecture
   ref/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
