from html import escape

import rdflib
from dirtyfields.compat import remote_field
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.contrib.postgres.fields import HStoreField, JSONField
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext, gettext_lazy as _
from dirtyfields import DirtyFieldsMixin
from django.utils import translation

from commons_api.wikidata.namespaces import WD, RDF, RDFS, WDT, SCHEMA, WIKIBASE
from commons_api.wikidata.utils import lang_dict, select_multilingual, item_uri_to_id


class Timebound(models.Model):
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)

    class Meta:
        abstract = True


class ModerationItem(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64, db_index=True)
    item = GenericForeignKey('content_type', 'object_id')
    data = JSONField(encoder=DjangoJSONEncoder)
    creation = models.BooleanField(default=False)
    deletion = models.BooleanField(default=False)

    def get_new_wikidata_item(self):
        model_class = self.content_type.model_class()
        try:
            wikidata_item = model_class.objects.get(id=self.object_id)
        except model_class.DoesNotExist:
            wikidata_item = model_class(id=self.object_id)
        for attr_name, value in self.data.items():
            setattr(wikidata_item, attr_name, value)
        return wikidata_item

    def apply(self):
        if self.deletion:
            model_class = self.content_type.model_class()
            model_class.objects.filter(id=self.object_id).delete()
        else:
            wikidata_item = self.get_new_wikidata_item()
            wikidata_item.save(moderated=True)
        self.delete()

    def get_absolute_url(self):
        return reverse('wikidata:moderationitem-detail', args=(self.id,))

    class Meta:
        index_together = (('content_type', 'object_id'),)


class Moderateable(DirtyFieldsMixin, models.Model):
    def save(self, *args, moderated=False, **kwargs):
        moderated = True
        ct = ContentType.objects.get_for_model(self)
        if not self.is_dirty():
            ModerationItem.objects.filter(content_type=ct, object_id=self.id).delete()
        elif not moderated and self.is_dirty():
            try:
                moderation_item = ModerationItem.objects.get(content_type=ct, object_id=self.id)
            except ModerationItem.DoesNotExist:
                moderation_item = ModerationItem(content_type=ct, object_id=self.id)
            moderation_data = {}
            for field_name in self.get_dirty_fields(check_relationship=True):
                field = self._meta.get_field(field_name)
                if remote_field(field):
                    field_name = field.get_attname()
                moderation_data[field_name] = getattr(self, field_name)
            moderation_item.data = moderation_data
            moderation_item.deletion = False
            if not type(self).objects.filter(id=self.id).exists():
                moderation_item.creation = True
            moderation_item.save()
        elif moderated:
            super().save(*args, **kwargs)
            ModerationItem.objects.filter(content_type=ct, object_id=self.id).delete()

    def delete(self, using=None, keep_parents=False, moderated=False):
        ct = ContentType.objects.get_for_model(self)
        if not moderated:
            try:
                moderation_item = ModerationItem.objects.get(content_type=ct, object_id=self.id)
            except ModerationItem.DoesNotExist:
                moderation_item = ModerationItem(content_type=ct, object_id=self.id)
            moderation_item.data = None
            moderation_item.deletion = True
            moderation_item.save()
        elif moderated:
            super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        abstract = True


class WikidataItemManager(models.Manager):
    def for_id_and_label(self, id, label, save=False):
        try:
            obj = self.get(id=id)
        except self.model.DoesNotExist:
            if save:
                obj = self.create(id=id, labels={'en': label})
            else:
                obj = self.model(id=id, labels={'en': label})
        return obj


class WikidataItem(Moderateable, Timebound):
    id = models.CharField(max_length=16, primary_key=True)
    labels = HStoreField(default=dict, blank=True)
    identifiers = HStoreField(default=dict, blank=True)
    wikipedia_article_links = HStoreField(default=dict, blank=True)
    wikipedia_article_titles = HStoreField(default=dict, blank=True)

    objects = WikidataItemManager()

    @property
    def uri(self):
        return WD[self.id]

    @property
    def label(self):
        return select_multilingual(self.labels, gettext('[no label]'))

    @property
    def wikipedia_article(self):
        return select_multilingual(self.wikipedia_articles)

    @property
    def link(self):
        return mark_safe('<a href="{}" class="item-link item-link-{}">{}</a>'.format(escape(self.get_absolute_url()),
                                                                                     self._meta.model_name,
                                                                                     escape(self.label, quote=False)))

    @property
    def wikipedia_articles(self):
        return {language: {'href': self.wikipedia_article_links[language],
                           'title': self.wikipedia_article_titles[language]}
                for language in self.wikipedia_article_links}

    def update_from_entity_data(self, graph: rdflib.Graph):
        self.labels = lang_dict(graph.objects(self.uri, RDFS.label))
        for prop, attr in getattr(self, 'wikidata_mapping', ()):
            field = self._meta.get_field(attr)
            value = graph.value(self.uri, WDT[prop], default=None)
            if isinstance(field, (models.CharField, models.IntegerField, models.DateField)):
                if value is None and not field.null:
                    value = ''
                setattr(self, attr, value)
            elif isinstance(field, models.ForeignKey):
                if value:
                    referent = field.related_model.objects.for_id_and_label(item_uri_to_id(value), '')
                    referent.update_from_entity_data(graph)
                    referent.save()
                    setattr(self, attr, referent)
                else:
                    setattr(self, attr, None)
            else:
                raise TypeError("Unexpected target field type: {}".format(field))

        self.wikipedia_article_links, self.wikipedia_article_titles = {}, {}
        for article in graph.subjects(SCHEMA.about, self.uri):
            if (article, RDF.type, SCHEMA.Article) not in graph:
                continue
            article_is_part_of = graph.value(article, SCHEMA.isPartOf, None)
            if not article_is_part_of:
                continue
            if graph.value(article_is_part_of, WIKIBASE.wikiGroup, None) != rdflib.Literal('wikipedia'):
                continue
            language = str(graph.value(article, SCHEMA.inLanguage))
            self.wikipedia_article_links[language] = str(article)
            self.wikipedia_article_titles[language] = str(graph.value(article, SCHEMA.name))

    def __str__(self):
        return self.label

    def get_absolute_url(self):
        model_name = ContentType.objects.get_for_model(self).model
        return reverse('wikidata:{}-detail'.format(model_name), args=(self.id,))

    class Meta:
        abstract = True


class Term(WikidataItem):
    """A taxonomy term used in qualifiers (e.g. 'death in office')"""
    pass


class Country(WikidataItem):
    flag_image = models.URLField(null=True, blank=True)
    population = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'countries'

    wikidata_mapping = (
        ('P1082', 'population'),
        ('P41', 'flag_image'),
    )


class Person(WikidataItem):
    facebook_id = models.CharField(max_length=100, blank=True)
    twitter_id = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)
    sex_or_gender = models.ForeignKey(Term, null=True, blank=True, on_delete=models.CASCADE)

    wikidata_mapping = (
        ('P2013', 'facebook_id'),
        ('P2002', 'twitter_id'),
        ('P18', 'image_url'),
        ('P21', 'sex_or_gender'),
    )


class AdministrativeArea(WikidataItem):
    pass


class ElectoralDistrict(WikidataItem):
    pass


class Position(WikidataItem):
    pass


class LegislativeTerm(WikidataItem):
    position = models.ForeignKey(Position, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ('start', 'end')


class LegislativeHouse(WikidataItem):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    administrative_area = models.ForeignKey(AdministrativeArea, on_delete=models.CASCADE)
    positions = models.ManyToManyField(Position)
    legislative_terms = models.ManyToManyField(LegislativeTerm, through='LegislativeHouseTerm')


class LegislativeHouseTerm(Moderateable, models.Model):
    id = models.CharField(max_length=128, primary_key=True)
    legislative_term = models.ForeignKey(LegislativeTerm, on_delete=models.CASCADE)
    legislative_house = models.ForeignKey(LegislativeHouse, on_delete=models.CASCADE)
    term_specific_position = models.ForeignKey(Position, null=True, blank=True, on_delete=models.CASCADE)
    number_of_seats = models.IntegerField(null=True, blank=True)
    number_of_districts = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.id = '{}/{}'.format(self.legislative_house_id, self.legislative_term_id)
        return super().save(*args, **kwargs)


class Election(WikidataItem):
    pass


class Membership(Timebound, Moderateable):
    id = models.CharField(max_length=64, primary_key=True)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class LegislativeMembership(Membership):
    legislative_house = models.ForeignKey(LegislativeHouse, on_delete=models.CASCADE)
    legislative_terms = models.ManyToManyField(LegislativeTerm, blank=True)
    district = models.ForeignKey(ElectoralDistrict, null=True, blank=True, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, null=True, blank=True, on_delete=models.CASCADE)
    end_cause = models.ForeignKey(Term, null=True, blank=True, on_delete=models.CASCADE,
                                  related_name='end_cause_of_legislative_memberships')
    subject_has_role = models.ForeignKey(Term, null=True, blank=True, on_delete=models.CASCADE,
                                         related_name='subject_role_of_legislative_memberships')

    class Meta:
        ordering = ('start', 'end')