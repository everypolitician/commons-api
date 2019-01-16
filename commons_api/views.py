import ast
import datetime
import itertools
import json
import re

from django.apps import apps
from django.views.generic import TemplateView

from django_celery_results.models import TaskResult

from commons_api.wikidata.models import WikidataItem


class QueueStatusView(TemplateView):
    template_name = 'commons_api/queue-status.html'
    is_wikidata_item_id = re.compile('^Q[1-9][0-9]*$').match

    def parse_task(self, task):
        if isinstance(task, TaskResult):
            task = task.as_dict()
            task['name'] = task.pop('task_name')
            task['args'] = task.pop('task_args')
        try:
            parsed_args = ast.literal_eval(task['args'])
        except ValueError:
            parsed_args = []
        if 'time_start' in task:
            task['time_start'] = datetime.datetime.fromtimestamp(task['time_start'])
        task.update({
            'name': task['name'].split('.')[-1].replace('_', ' '),
            'parsed_args': parsed_args,
        })
        return task

    def parse_tasks(self, tasks):
        data = [self.parse_task(task) for task in tasks]
        wikidata_ids = {arg
                        for result in data
                        for arg in result['parsed_args']
                        if self.is_wikidata_item_id(arg)}
        wikidata_links = {}
        for model in apps.get_models():
            if issubclass(model, WikidataItem):
                wikidata_links.update({item.id: item.link
                                       for item in model.objects.filter(id__in=wikidata_ids)})
        for result in data:
            result['parsed_args'] = [wikidata_links.get(arg, arg)
                                     for arg in result['parsed_args']]
        return data

    def get_active_tasks(self):
        from commons_api import celery_app
        return self.parse_tasks(list(itertools.chain(*celery_app.control.inspect().active().values())))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'active_tasks': self.get_active_tasks(),
            'taskresults': self.parse_tasks(TaskResult.objects.order_by('-pk')[:20]),
        })
        return context
