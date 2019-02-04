import http.client

from django.test import TestCase
from django.urls import reverse
from django.views.generic import ListView, DetailView

from .. import models, views


class ViewTestCaseMixin(object):
    view_class = None

    fixtures = ['view-tests']

    def get_object(self):
        return None

    def get_url(self, object=None):
        if isinstance(self.view, ListView):
            return reverse('wikidata:{}-list'.format(self.view.model._meta.model_name))
        elif isinstance(self.view, DetailView):
            return object.get_absolute_url()

    def setUp(self):
        self.view = self.view_class()

    def testGet(self):
        if isinstance(self.view, ListView):
            response = self.client.get(self.get_url())
            self.assertEqual(http.client.OK, response.status_code)
        elif isinstance(self.view, DetailView):
            if not self.view.model.objects.count():
                raise AssertionError("You need to create some {} objects to test".format(self.view.model))
            for obj in self.view.model.objects.all():
                response = self.client.get(self.get_url(obj))
                self.assertEqual(http.client.OK, response.status_code)


class CountryListViewTestCase(ViewTestCaseMixin, TestCase):
    view_class = views.CountryListView


class CountryDetailViewTestCase(ViewTestCaseMixin, TestCase):
    view_class = views.CountryDetailView


class LegislativeHouseDetailViewTestCase(ViewTestCaseMixin, TestCase):
    view_class = views.LegislativeHouseDetailView


class LegislativeTermDetailViewTestCase(ViewTestCaseMixin, TestCase):
    view_class = views.LegislativeTermDetailView


class LegislativeHouseMembershipViewTestCase(ViewTestCaseMixin, TestCase):
    fixtures = ['view-tests']
    view_class = views.LegislativeHouseMembershipView

    def testAllMembers(self):
        for house in models.LegislativeHouse.objects.all():
            response = self.client.get(reverse('wikidata:legislativehouse-membership-all',
                                               kwargs={'pk': house.pk}))
            self.assertEqual(http.client.OK, response.status_code)

    def testCurrentMembers(self):
        for house in models.LegislativeHouse.objects.all():
            response = self.client.get(reverse('wikidata:legislativehouse-membership-current',
                                               kwargs={'pk': house.pk}))
            self.assertEqual(http.client.OK, response.status_code)

    def testTermMembers(self):
        for house in models.LegislativeHouse.objects.all():
            for term in house.legislative_terms.all():
                response = self.client.get(reverse('wikidata:legislativehouse-membership-term',
                                                   kwargs={'pk': house.pk,
                                                           'legislativeterm_pk': term.pk}))
                self.assertEqual(http.client.OK, response.status_code)
