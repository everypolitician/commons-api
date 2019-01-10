import datetime

from django.db import models
from django.db.models import Q
from django.db.models.manager import BaseManager


class TimeboundQuerySet(models.QuerySet):
    def overlaps_range(self, start, end):
        qs = self
        if start:
            qs = qs.filter(Q(end__isnull=True) | Q(end__gte=start))
        if end:
            qs = qs.filter(Q(start__isnull=True) | Q(start__lte=end))
        return qs

    def current(self):
        return self.overlaps_range(datetime.date.today(), datetime.date.today())

    def overlaps(self, obj):
        # type: (Timebound) -> TimeboundQuerySet
        return self.overlaps_range(obj.start, obj.end)


class TimeboundManager(BaseManager.from_queryset(TimeboundQuerySet)):
    pass


class WikidataItemManager(TimeboundManager):
    def for_id_and_label(self, id, label, save=False):
        try:
            obj = self.get(id=id)
        except self.model.DoesNotExist:
            if save:
                obj = self.create(id=id, labels={'en': label})
            else:
                obj = self.model(id=id, labels={'en': label})
        return obj

