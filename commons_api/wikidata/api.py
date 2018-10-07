from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()

router.register('legislative-membership', viewsets.LegislativeMembershipViewSet)
