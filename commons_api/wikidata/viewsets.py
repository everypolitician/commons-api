from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.viewsets import ReadOnlyModelViewSet

from . import models, renderers, serializers


class LegislativeMembershipViewSet(ReadOnlyModelViewSet):
    queryset = models.LegislativeMembership.objects.filter(legislative_house_id='Q11005')
    serializer_class = serializers.LegislativeMembershipSerializer
    renderer_classes = (
        BrowsableAPIRenderer,
        JSONRenderer,
        renderers.PopoloJSONRenderer,
    )
