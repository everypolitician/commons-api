from django.contrib.postgres.fields import HStoreField
from django.db import models

from commons_api.wikidata.models import Country


class Shapefile(models.Model):
    url = models.URLField(unique=True)
    etags = HStoreField(default=dict)
