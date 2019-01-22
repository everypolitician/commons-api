from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()

router.register('country', viewsets.CountryViewSet)
router.register('electoral-district', viewsets.ElectoralDistrictViewSet)
router.register('legislative-membership', viewsets.LegislativeMembershipViewSet)
