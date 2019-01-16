from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import path, include, re_path

from . import views

admin.autodiscover()

urlpatterns = [
    path('queue-status', views.QueueStatusView.as_view(), name='queue-status'),
    path('', TemplateView.as_view(template_name='index.html')),
    path('', include('commons_api.wikidata.urls', 'wikidata')),
    re_path('^(?=boundaries|boundary-sets/)', include('boundaries.urls')),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
