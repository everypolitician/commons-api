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

        if created:
            queued_at = timezone.now()
            sender.objects.filter(id=instance.id).update(refresh_members_last_queued=queued_at,
                                                         refresh_districts_last_queued=queued_at)
            refresh_members.delay(id=instance.id, queued_at=queued_at)
            refresh_districts.delay(id=instance.id, queued_at=queued_at)
