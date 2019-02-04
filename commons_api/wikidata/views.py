import datetime

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models.fields.related import RelatedField
from django.shortcuts import redirect
from django.urls import reverse, get_resolver, resolve
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import ContextMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView
from operator import attrgetter

from django.views.generic import ListView, DetailView, FormView
from rest_framework.utils.urls import replace_query_param

from commons_api.wikidata import tasks
from . import forms, models


class APILinksMixin(ContextMixin):
    api_format_names = {
        'api': _('Browsable API'),
        'json': _('JSON'),
        'geojson': _('GeoJSON'),
        'popolo-json': _('Popolo JSON'),
    }

    def get_api_base_urls(self):
        if isinstance(self, ListView):
            return [(
                self.model._meta.verbose_name_plural,
                reverse('wikidata:api:{}-list'.format(self.model._meta.model_name))
            )]
        elif isinstance(self, DetailView):
            return [(
                self.model._meta.verbose_name,
                reverse('wikidata:api:{}-detail'.format(self.model._meta.model_name),
                        kwargs={'pk': self.object.pk})
            )]
        else:
            raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        api_base_urls = self.get_api_base_urls()
        if api_base_urls:
            context['api_urls'] = []
            for name, base_url in api_base_urls:
                api_view = resolve(base_url.split('?')[0]).func.cls
                context['api_urls'].append({
                    'name': name,
                    'urls': [{
                        'format': renderer.format,
                        'name': self.api_format_names[renderer.format],
                        'url': replace_query_param(base_url, 'format', renderer.format)
                    } for renderer in api_view.renderer_classes],
                })
        return context


class CountryListView(APILinksMixin, ListView):
    model = models.Country
    template_name = 'wikidata/country_list.html'
    context_object_name = 'country_list'

    def post(self, request, *args, **kwargs):
        if 'refresh-country-list' in request.POST:
            tasks.refresh_country_list.delay()
            messages.info(request, "Country list will be refreshed")
        if 'update-all-boundaries' in request.POST:
            from commons_api.proto_commons.tasks import update_all_boundaries
            update_all_boundaries.delay()
            messages.info(request, "All boundaries will be refreshed")
        return redirect(self.request.build_absolute_uri())

    def get_queryset(self):
        # Sort in the user's chosen language
        return sorted(super().get_queryset(), key=attrgetter('label'))


class CountryDetailView(APILinksMixin, DetailView):
    model = models.Country

    def get_api_base_urls(self):
        return [
            *super().get_api_base_urls(),
            ('legislative houses',
             reverse('wikidata:api:legislativehouse-list') + '?country=' + self.object.id),
        ]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'refresh-legislature-list' in request.POST:
            self.object.refresh_legislatures_last_queued = timezone.now()
            self.object.save()
            tasks.refresh_legislatures.delay(self.object.id, queued_at=self.object.refresh_legislatures_last_queued)
            messages.info(request, "Legislature list for {} will "
                                   "be refreshed".format(self.object))
        if 'update-boundaries' in request.POST:
            from commons_api.proto_commons.tasks import update_boundaries_for_country
            update_boundaries_for_country.delay(self.object.id)
            messages.info(request, "Boundaries for {} will "
                                   "be refreshed".format(self.object))

        return redirect(self.object.get_absolute_url())


class LegislativeHouseDetailView(APILinksMixin, DetailView):
    model = models.LegislativeHouse

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'refresh-legislature-members' in request.POST:
            self.object.refresh_members_last_queued = timezone.now()
            self.object.save()
            tasks.refresh_members.delay(self.object.id, queued_at=self.object.refresh_members_last_queued)
            messages.info(request, "Legislature membership for {} "
                                   "will be refreshed".format(self.object))
        if 'refresh-legislature-districts' in request.POST:
            self.object.refresh_districts_last_queued = timezone.now()
            self.object.save()
            tasks.refresh_districts.delay(self.object.id, queued_at=self.object.refresh_districts_last_queued)
            messages.info(request, "Legislature districts for {} "
                                   "will be refreshed".format(self.object))
        return redirect(self.object.get_absolute_url())


class ElectoralDistrictDetailView(DetailView):
    model = models.ElectoralDistrict


class LegislativeTermDetailView(DetailView):
    model = models.LegislativeTerm


class PersonDetailView(DetailView):
    model = models.Person


class LegislativeHouseMembershipView(APILinksMixin, DetailView):
    model = models.LegislativeHouse
    template_name_suffix = '_membership'
    all_members = False
    current_members = False

    def get_api_base_urls(self):
        if self.current_members:
            query_string = 'current_members'
        elif self.all_members:
            query_string = 'all_members'
        elif self.legislative_term:
            query_string = 'legislative_term=' + self.legislative_term.pk

        return [(
            'memberships',
            reverse('wikidata:api:legislativehouse-memberships-detail',
                    kwargs={'pk': self.object.pk}) + '?' + query_string,
        )]

    @cached_property
    def legislative_house_term(self):
        if 'legislativeterm_pk' in self.kwargs:
            return models.LegislativeHouseTerm.objects.get(
                legislative_house=self.object,
                legislative_term_id=self.kwargs['legislativeterm_pk'],
            )

    @cached_property
    def legislative_term(self):
        if self.legislative_house_term:
            return self.legislative_house_term.legislative_term

    @cached_property
    def districts(self):
        return self.object.get_districts(
            only_current=self.current_members,
            legislative_term=self.legislative_term
        )

    @cached_property
    def memberships(self):
        return self.object.get_memberships(
            require_start=not self.all_members,
            only_current=self.current_members,
            legislative_term=self.legislative_term
        ).select_related('parliamentary_group', 'party', 'district', 'person', 'person__sex_or_gender')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context.update({
            'legislativehouseterm': self.legislative_house_term,
            'legislativeterm': self.legislative_term,
            'districts': self.districts,
            'memberships': self.memberships,
            'current_members': self.current_members,
            'all_members': self.all_members,
        })
        return context


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
