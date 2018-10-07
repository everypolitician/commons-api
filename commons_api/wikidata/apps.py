from django import apps
from django.db.models.signals import post_save

class CountryConfig(apps.AppConfig):
    name = 'commons_api.wikidata'

    def ready(self):
        from commons_api.wikidata import models

        #post_save.connect(self.refresh_from_entity_data_when_created)
        post_save.connect(self.refresh_legislatures_when_country_created, sender=models.Country)
        post_save.connect(self.refresh_memberships_when_legislature_created, sender=models.LegislativeHouse)

    def refresh_from_entity_data_when_created(self, sender, instance, created, **kwargs):
        from commons_api.wikidata import models
        from commons_api.wikidata.tasks import refresh_from_entity_data
        from django.contrib.contenttypes.models import ContentType

        if created and issubclass(sender, models.WikidataItem):
            ct = ContentType.objects.get_for_model(sender)
            refresh_from_entity_data.delay(ct.app_label, ct.model, instance.id)

    def refresh_legislatures_when_country_created(self, instance, created, **kwargs):
        from commons_api.wikidata.tasks import refresh_legislature_list

        if created:
            refresh_legislature_list.delay(instance.id)

    def refresh_memberships_when_legislature_created(self, instance, created, **kwargs):
        from commons_api.wikidata.tasks import refresh_legislature_members

        if created:
            refresh_legislature_members.delay(instance.id)
