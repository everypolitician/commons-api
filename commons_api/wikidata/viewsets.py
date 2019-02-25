from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet

from . import models, renderers, serializers


class CountryViewSet(ReadOnlyModelViewSet):
    queryset = models.Country.objects.all().select_related('boundary')
    serializer_class = serializers.CountrySerializer
    renderer_classes = (
        JSONRenderer,
        BrowsableAPIRenderer,
        renderers.GeoJSONRenderer,
    )


class ElectoralDistrictViewSet(ReadOnlyModelViewSet):
    queryset = models.ElectoralDistrict.objects.all()
    serializer_class = serializers.ElectoralDistrictSerializer
    filter_fields = ('legislative_house',)
    filter_backends = (
        DjangoFilterBackend,
    )
    renderer_classes = (
        JSONRenderer,
        BrowsableAPIRenderer,
        renderers.GeoJSONRenderer,
    )


class LegislativeHouseViewSet(ReadOnlyModelViewSet):
    queryset = models.LegislativeHouse.objects.select_related('administrative_area')
    serializer_class = serializers.LegislativeHouseSerializer
    filter_fields = ('country',)
    filter_backends = (
        DjangoFilterBackend,
    )


class LegislativeHouseMembershipViewSet(RetrieveModelMixin, GenericViewSet):
    queryset = models.LegislativeHouse.objects.all()
    serializer_class = serializers.LegislativeHouseMembershipSerializer
    renderer_classes = (
        JSONRenderer,
        BrowsableAPIRenderer,
        renderers.PopoloJSONRenderer,
        renderers.PopoloGeoJSONRenderer,
    )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if 'legislative_term' in self.request.GET:
            context['legislative_term'] = get_object_or_404(models.LegislativeTerm,
                                                            pk=self.request.GET['legislative_term'])
        context['all_members'] = 'all_members' in self.request.GET
        context['current_members'] = 'current_members' in self.request.GET
        return context

