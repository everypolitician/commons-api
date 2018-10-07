import datetime
from django.db.models import Q
from django.utils.functional import cached_property
from operator import attrgetter

from django.views.generic import ListView, DetailView

from . import models


class CountryListView(ListView):
    model = models.Country
    template_name = 'wikidata/country_list.html'
    context_object_name = 'country_list'

    def get_queryset(self):
        # Sort in the user's chosen language
        return sorted(super().get_queryset(), key=attrgetter('label'))


class CountryDetailView(DetailView):
    model = models.Country


class LegislativeHouseDetailView(DetailView):
    model = models.LegislativeHouse


class LegislativeTermDetailView(DetailView):
    model = models.LegislativeTerm


class PersonDetailView(DetailView):
    model = models.Person


class LegislativeMembershipListView(ListView):
    model = models.LegislativeMembership

    @cached_property
    def legislative_house_term(self):
        if 'legislativeterm_pk' in self.kwargs:
            return models.LegislativeHouseTerm.objects.get(legislative_house=self.legislative_house,
                                                           legislative_term_id=self.kwargs['legislativeterm_pk'])

    @cached_property
    def legislative_house(self):
        return models.LegislativeHouse.objects.get(id=self.kwargs['legislativehouse_pk'])

    @cached_property
    def legislative_term(self):
        if self.legislative_house_term:
            return self.legislative_house_term.legislative_term

    @cached_property
    def start(self):
        return self.legislative_term.start if self.legislative_term else datetime.date.today()

    @cached_property
    def end(self):
        return self.legislative_term.end if self.legislative_term else datetime.date.today()

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context.update({
            'legislativehouseterm': self.legislative_house_term,
            'legislativehouse': self.legislative_house,
            'legislativeterm': self.legislative_term,
            'start': self.start,
            'end': self.end,
        })
        return context

    def get_queryset(self):
        qs = super().get_queryset().filter(legislative_house_id=self.kwargs['legislativehouse_pk'])
        qs = qs.filter(start__isnull=False)
        if self.start:
            qs = qs.filter(Q(end__isnull=True) | Q(end__gte=self.start))
        if self.end:
            qs = qs.filter(Q(start__isnull=True) | Q(start__lte=self.end))
        return qs.select_related('district', 'person', 'person__sex_or_gender')


class ModerationItemDetailView(DetailView):
    model = models.ModerationItem

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = context['object']
        old_wikidata_item = obj.item
        if old_wikidata_item is None:
            old_wikidata_item = obj.content_type.model_class()()
        new_wikidata_item = obj.get_new_wikidata_item()
        print(old_wikidata_item, new_wikidata_item)
        return {
            **context,
            'model_meta': old_wikidata_item._meta,
            'old_wikidata_item': old_wikidata_item,
            'new_wikidata_item': new_wikidata_item,
            'fields': [{
                'field_name': field.name,
                'old_value': getattr(old_wikidata_item, field.name),
                'new_value': getattr(new_wikidata_item, field.name),
                'changed': getattr(old_wikidata_item, field.name) != getattr(new_wikidata_item, field.name),
            } for field in old_wikidata_item._meta.fields],
        }
