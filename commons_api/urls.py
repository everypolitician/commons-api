from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import RedirectView
from django.urls import path, include

admin.autodiscover()

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='wikidata:country-list')),
    path('', include('commons_api.wikidata.urls', 'wikidata')),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
