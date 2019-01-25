from django import apps
from django.db.models.signals import post_save
from django.utils import timezone


class CountryConfig(apps.AppConfig):
    name = 'commons_api.wikidata'

    def ready(self):
        from commons_api.wikidata import models

        post_save.connect(self.refresh_legislatures_when_country_created,
                          sender=models.Country)
        post_save.connect(self.refresh_when_legislature_created,
                          sender=models.LegislativeHouse)
        post_save.connect(self.refresh_geoshape_when_spatial_created)

    def refresh_legislatures_when_country_created(self, sender, instance, created, **kwargs):
        from commons_api.wikidata.tasks import refresh_legislatures

        if created and not instance.refresh_legislatures_last_queued:
            queued_at = timezone.now()
            sender.objects.filter(id=instance.id).update(refresh_legislatures_last_queued=queued_at)
            refresh_legislatures.delay(id=instance.id, queued_at=queued_at)

    def refresh_when_legislature_created(self, sender, instance, created, **kwargs):
        from commons_api.wikidata.tasks import (
            refresh_members,
            refresh_districts,
        )

        if created and not instance.refresh_members_last_queued:
            queued_at = timezone.now()
            sender.objects.filter(id=instance.id).update(refresh_members_last_queued=queued_at,
                                                         refresh_districts_last_queued=queued_at)
            refresh_members.delay(id=instance.id, queued_at=queued_at)
            refresh_districts.delay(id=instance.id, queued_at=queued_at)

    def refresh_geoshape_when_spatial_created(self, sender, instance, created, **kwargs):
        from commons_api.wikidata.tasks import refresh_geoshape
        from commons_api.wikidata import models
        from django.contrib.contenttypes.models import ContentType

        if issubclass(sender, models.Spatial) and created and instance.geoshape_url and \
                not instance.refresh_geoshape_last_queued:
            queued_at = timezone.now()
            sender.objects.filter(id=instance.id).update(refresh_geoshape_last_queued=queued_at)
            ct = ContentType.objects.get_for_model(sender)
            refresh_geoshape.delay(ct.app_label, ct.model, instance.id, queued_at=queued_at)
