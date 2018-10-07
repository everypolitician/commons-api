from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from .. import models


class ModerationTestCase(TestCase):
    def test_creation_creates_moderation_item_and_doesnt_save(self):
        person = models.Person.objects.for_id_and_label('Q42', 'Douglas Adams', save=True)
        self.assertEqual(0, models.Person.objects.count())

        moderation_item = models.ModerationItem.objects.get()
        self.assertEqual(ContentType.objects.get_for_model(person), moderation_item.content_type)
        self.assertEqual(person.id, moderation_item.object_id)

    def test_apply_moderation_item(self):
        person = models.Person.objects.for_id_and_label('Q42', 'Douglas Adams', save=True)
        moderation_item = models.ModerationItem.objects.get()
        moderation_item.apply()
        new_person = models.Person.objects.get()
        self.assertEqual(person.id, new_person.id)
        self.assertEqual(person.labels, new_person.labels)