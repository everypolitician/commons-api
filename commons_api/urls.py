from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import path, include, re_path

admin.autodiscover()

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html')),
    path('', include('commons_api.wikidata.urls', 'wikidata')),
    re_path('^(?=boundaries|boundary-sets/)', include('boundaries.urls')),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
