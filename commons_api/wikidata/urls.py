from django.urls import path, include

from . import api, views

app_name = 'wikidata'

urlpatterns = (
    path('country', views.CountryListView.as_view(), name='country-list'),
    path('country/<pk>', views.CountryDetailView.as_view(), name='country-detail'),
    path('person/<pk>', views.PersonDetailView.as_view(), name='person-detail'),
    path('legislative-house/<pk>', views.LegislativeHouseDetailView.as_view(), name='legislativehouse-detail'),
    path('legislative-term/<pk>', views.LegislativeTermDetailView.as_view(), name='legislativeterm-detail'),
    path('legislative-memberships/<legislativehouse_pk>/current',
         views.LegislativeMembershipListView.as_view(), name='legislativemembership-list-current'),
    path('legislative-memberships/<legislativehouse_pk>/<legislativeterm_pk>',
         views.LegislativeMembershipListView.as_view(), name='legislativemembership-list'),

    path('moderate/<pk>', views.ModerationItemDetailView.as_view(), name='moderationitem-detail'),

    path('api/', include(api.router.get_urls()), name='api'),
)