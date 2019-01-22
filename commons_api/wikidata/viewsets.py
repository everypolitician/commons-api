from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.viewsets import ReadOnlyModelViewSet

from . import models, renderers, serializers


class CountryViewSet(ReadOnlyModelViewSet):
    queryset = models.Country.objects.all().select_related('boundary')
    serializer_class = serializers.CountrySerializer
    renderer_classes = (
        BrowsableAPIRenderer,
        JSONRenderer,
        renderers.GeoJSONRenderer,
    )


class LegislativeMembershipViewSet(ReadOnlyModelViewSet):
    queryset = models.LegislativeMembership.objects.filter(legislative_house_id='Q11005')
    serializer_class = serializers.LegislativeMembershipSerializer
    renderer_classes = (
        BrowsableAPIRenderer,
        JSONRenderer,
        renderers.PopoloJSONRenderer,
    )
