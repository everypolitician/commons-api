import datetime

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models.fields.related import RelatedField
from django.shortcuts import redirect
from django.utils.functional import cached_property
from django.views.generic.edit import ModelFormMixin, ProcessFormView
from operator import attrgetter

from django.views.generic import ListView, DetailView, FormView

from commons_api.wikidata import tasks
from . import forms, models


class CountryListView(ListView):
    model = models.Country
    template_name = 'wikidata/country_list.html'
    context_object_name = 'country_list'

    def post(self, request, *args, **kwargs):
        if 'refresh-country-list' in request.POST:
            tasks.refresh_country_list.delay()
            messages.info(request, "Country list will be refreshed")
        return redirect(self.request.build_absolute_uri())

    def get_queryset(self):
        # Sort in the user's chosen language
        return sorted(super().get_queryset(), key=attrgetter('label'))


class CountryDetailView(DetailView):
    model = models.Country

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'refresh-legislature-list' in request.POST:
            tasks.refresh_legislature_list.delay(self.object.id)
            messages.info(request, "Legislature list for {} will "
                                   "be refreshed".format(self.object))
        return redirect(self.object.get_absolute_url())


class LegislativeHouseDetailView(DetailView):
    model = models.LegislativeHouse

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'refresh-legislature-members' in request.POST:
            tasks.refresh_legislature_members.delay(self.object.id)
            messages.info(request, "Legislature membership for {} "
                                   "will be refreshed".format(self.object))
        if 'refresh-legislature-districts' in request.POST:
            tasks.refresh_legislature_districts.delay(self.object.id)
            messages.info(request, "Legislature districts for {} "
                                   "will be refreshed".format(self.object))
        return redirect(self.object.get_absolute_url())


class ElectoralDistrictDetailView(DetailView):
    model = models.ElectoralDistrict


class LegislativeTermDetailView(DetailView):
    model = models.LegislativeTerm


class PersonDetailView(DetailView):
    model = models.Person


class LegislativeMembershipListView(ListView):
    model = models.LegislativeMembership
    all_members = False
    current_members = False

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
            'current_members': self.current_members,
            'all_members': self.all_members,
        })
        return context

    def get_queryset(self):
        qs = super().get_queryset().filter(legislative_house_id=self.kwargs['legislativehouse_pk']) \
            .select_related('parliamentary_group', 'party', 'district')
        if not self.all_members:
            qs = qs.filter(start__isnull=False)
        if self.legislative_term:
            qs = qs.overlaps(self.legislative_term)
        elif self.current_members:
            qs = qs.current()
        qs = qs.select_related('district', 'person', 'person__sex_or_gender')
        return qs


class ModerationItemDetailView(ModelFormMixin, ProcessFormView, DetailView):
    model = models.ModerationItem
    form_class = forms.ModerateForm

    def get_item_attribute(self, item, field):
        if isinstance(field, RelatedField):
            try:
                return getattr(item, field.name)
            except field.related_model.DoesNotExist:
                try:
                    return models.ModerationItem.objects.get(
                        content_type=ContentType.objects.get_for_model(field.related_model),
                        object_id=getattr(item, field.get_attname()),
                    )
                except models.ModerationItem.DoesNotExist:
                    return getattr(item, field.get_attname())
        else:
            return getattr(item, field.name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = context['object']
        old_wikidata_item = obj.item
        if old_wikidata_item is None:
            old_wikidata_item = obj.content_type.model_class()()
        new_wikidata_item = obj.get_new_wikidata_item()
        return {
            **context,
            'model_meta': old_wikidata_item._meta,
            'old_wikidata_item': old_wikidata_item,
            'new_wikidata_item': new_wikidata_item,
            'fields': [{
                'field_name': field.name,
                'old_value': self.get_item_attribute(old_wikidata_item, field),
                'new_value': self.get_item_attribute(new_wikidata_item, field),
                'changed': getattr(old_wikidata_item, field.get_attname()) != getattr(new_wikidata_item, field.get_attname()),
            } for field in old_wikidata_item._meta.fields],
        }
