import datetime
import inspect

import celery
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from .. import models


def get_wikidata_model_by_name(app_label, model, superclass=models.WikidataItem):
    ct = ContentType.objects.get_by_natural_key(app_label, model)
    model = ct.model_class()
    if not issubclass(model, superclass):
        raise TypeError('Model {} with content_type {}.{} is not a {}'.format(model, app_label, model, superclass))
    return model


def get_wikidata_models(superclass=models.WikidataItem):
    return [model for model in apps.get_models() if issubclass(model, superclass)]


def with_periodic_queuing_task(last_queued_attribute=None,
                               superclass=models.WikidataItem,
                               queryset_filter=None):
    """A decorator that creates a task that will call the decorated task for objects that haven't been refreshed recently

    Usage:

    @with_periodic_queuing_task('update_geoshape_last_queued', Spatial, queryset_filter=lambda qs: qs.filter(…))
    @celery.shared_task
    def update_geoshape(…):
        …

    Or:

    @with_periodic_queuing_task
    @celery.shared_task
    def update_geoshape(…):
        …

    The decorated task can take the following parameters:

    * queued_at (required):
    * id (optional): A Wikidata ID. If this is present, the task will be queued once per object. If it is absent,
          it is assumed that the task can find all items to act upon based on `queued_at`.


    :param last_queued_attribute: The name of the attribute which records when an object was last queued to have the
        decorated task act upon it. If omitted, defaults to the name of the task with '_last_queued' appended
    :param superclass: A model superclass for which the task is relevant
    :param queryset_filter: If given, a function that will be applied to a queryset to further restrict items that
        this task applies to
    :returns: A decorator, which can be applied to a celery task
    """
    if callable(last_queued_attribute):
        # This means the function has been applied directly to the task, as per the second example above
        return with_periodic_queuing_task()(last_queued_attribute)

    # This is the actual decorator function which will be applied to the task function
    def decorator(task):
        nonlocal last_queued_attribute

        # Generate a field name if one wasn't provided, based on the task name. This is used to record when the task was
        # last queued for particular Wikidata items
        if not last_queued_attribute:
            last_queued_attribute = task.__name__ + '_last_queued'
        try:
            superclass._meta.get_field(last_queued_attribute)
        except KeyError:
            raise ValueError(
                f"last_queued_attribute ({last_queued_attribute}) should be a field on {superclass.__name__}")

        # We'll use the task signature to pass the right arguments to the task
        task_signature = inspect.signature(task)

        def queuing_task(not_queued_in=datetime.timedelta(7)):
            queued_at = timezone.now()
            if isinstance(not_queued_in, (int, float)):
                # Interpret as seconds
                not_queued_in = datetime.timedelta(0, not_queued_in)
            last_queued_threshold = queued_at - not_queued_in

            for model in get_wikidata_models(superclass):
                # Find all objects that haven't been queued recently, or have never been queued.
                queryset = model.objects.filter(Q(**{last_queued_attribute + '__lt': last_queued_threshold}) |
                                                Q(**{last_queued_attribute + '__isnull': True}))
                if queryset_filter:
                    queryset = queryset_filter(queryset)
                # Try to update any matching objects, and if any have been updated, we'll be queuing the task for them.
                if queryset.update(**{last_queued_attribute: queued_at}) > 0:
                    task_kwargs = {'queued_at': queued_at}
                    # Some tasks are generic and work across more than one model. To do this, they expect to be told
                    # which model they are acting on through `app_label` and `model` parameters. These are then looked
                    # up in the task with `get_wikidata_model_by_name`.
                    if 'model' in task_signature.parameters:
                        ct = ContentType.objects.get_for_model(model)
                        task_kwargs['app_label'] = ct.app_label
                        task_kwargs['model'] = ct.model
                    # As per the docstring, if the task takes an `id` parameter, we need to queue the task for each
                    # object individually.
                    if 'id' in task_signature.parameters:
                        filter_kwargs = {last_queued_attribute: queued_at}
                        # We don't need to apply queryset_filter here, as only objects filtered with it above will
                        # have a matching last_queued value
                        for item_id in model.objects.filter(**filter_kwargs).values_list('id', flat=True):
                            task.delay(id=item_id, **task_kwargs)
                    else:
                        task.delay(**task_kwargs)

        # We need to give the new task function a sensible __name__ and __module__ so that celery can construct a
        # task name for it (which we can refer to in e.g. commons_api.celery.app.conf.beat_schedule. We also make the
        # periodic queuing task an attribute on the original task so we can refer to it in code.
        queuing_task.__name__ = task.__name__ + '_queue_periodically'
        queuing_task.__module__ = task.__module__
        task.periodic_queuing_task = celery.shared_task(queuing_task)
        return task

    return decorator
