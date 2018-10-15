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
    path('legislative-memberships/<legislativehouse_pk>/current',
         views.LegislativeMembershipListView.as_view(current_members=True), name='legislativemembership-list-current'),
    path('legislative-memberships/<legislativehouse_pk>/all',
         views.LegislativeMembershipListView.as_view(all_members=True), name='legislativemembership-list-all'),

    path('legislative-memberships/<legislativehouse_pk>/<legislativeterm_pk>',
         views.LegislativeMembershipListView.as_view(), name='legislativemembership-list'),

    path('moderate/<pk>', views.ModerationItemDetailView.as_view(), name='moderationitem-detail'),

    path('api/', include(api.router.get_urls()), name='api'),
)