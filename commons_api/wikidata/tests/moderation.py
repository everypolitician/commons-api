from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from .. import models


@override_settings(ENABLE_MODERATION=True)
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

    def test_with_foreign_key_id(self):
        term = models.Term(id='Q1', labels={'en': 'term'})
        term.save(moderated=True)
        person = models.Person(id='Q2', labels={'en': 'person'}, sex_or_gender_id='Q1')
        person.save()

        moderation_item = models.ModerationItem.objects.get()
        self.assertEqual('Q1', moderation_item.data['sex_or_gender_id'])

    def test_with_foreign_key_object(self):
        term = models.Term(id='Q1', labels={'en': 'term'})
        term.save(moderated=True)
        person = models.Person(id='Q2', labels={'en': 'person'}, sex_or_gender=term)
        person.save()

        moderation_item = models.ModerationItem.objects.get()
        self.assertEqual('Q1', moderation_item.data['sex_or_gender_id'])

    def test_with_unsaved_foreign_key_id(self):
        term = models.Term(id='Q1', labels={'en': 'term'})
        term.save()
        person = models.Person(id='Q2', labels={'en': 'person'}, sex_or_gender_id='Q1')
        person.save()

        moderation_item = models.ModerationItem.objects.get(object_id='Q2')
        self.assertEqual('Q1', moderation_item.data['sex_or_gender_id'])

    def test_with_unsaved_foreign_key_object(self):
        term = models.Term(id='Q1', labels={'en': 'term'})
        term.save()
        person = models.Person(id='Q2', labels={'en': 'person'}, sex_or_gender=term)
        person.save()

        moderation_item = models.ModerationItem.objects.get(object_id='Q2')
        self.assertEqual('Q1', moderation_item.data['sex_or_gender_id'])

    def test_delete(self):
        term = models.Term(id='Q1', labels={'en': 'term'})
        term.save(moderated=True)
        term.delete()
        self.assertEqual(1, models.Term.objects.count())
        self.assertEqual(1, models.ModerationItem.objects.count())
        moderation_item = models.ModerationItem.objects.get()
        self.assertTrue(moderation_item.deletion)
        moderation_item.apply()
        self.assertEqual(0, models.Term.objects.count())
        self.assertEqual(0, models.ModerationItem.objects.count())

    def test_only_changing_relationships(self):
        term = models.Term(id='Q1', labels={'en': 'term'})
        term.save(moderated=True)
        person = models.Person(id='Q2', labels={'en': 'person'})
        person.save(moderated=True)
        self.assertEqual(0, models.ModerationItem.objects.count())
        person.sex_or_gender = term
        person.save()
        self.assertEqual(1, models.ModerationItem.objects.count())
