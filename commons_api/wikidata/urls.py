from django.urls import path, include

from . import api, views

app_name = 'wikidata'

urlpatterns = (
    path('country', views.CountryListView.as_view(), name='country-list'),
    path('country/<pk>', views.CountryDetailView.as_view(), name='country-detail'),
    path('person/<pk>', views.PersonDetailView.as_view(), name='person-detail'),
    path('legislative-house/<pk>', views.LegislativeHouseDetailView.as_view(), name='legislativehouse-detail'),
    path('legislative-term/<pk>', views.LegislativeTermDetailView.as_view(), name='legislativeterm-detail'),
    path('electoral-district/<pk>', views.ElectoralDistrictDetailView.as_view(), name='electoraldistrict-detail'),

    path('legislative-memberships/<pk>/current',
         views.LegislativeHouseMembershipView.as_view(current_members=True), name='legislativehouse-membership-current'),
    path('legislative-memberships/<pk>/all',
         views.LegislativeHouseMembershipView.as_view(all_members=True), name='legislativehouse-membership-all'),
    path('legislative-memberships/<pk>/<legislativeterm_pk>',
         views.LegislativeHouseMembershipView.as_view(), name='legislativehouse-membership-term'),

    path('moderate/<pk>', views.ModerationItemDetailView.as_view(), name='moderationitem-detail'),

    path('api/', include(api.router.get_urls()), name='api'),
)