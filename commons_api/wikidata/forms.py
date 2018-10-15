from django import forms
from django.utils.translation import gettext_lazy as _

from . import models


ACTION_CHOICES = (
    ('accept', _('Accept')),
    ('reject', _('Reject')),
)


class ModerateForm(forms.ModelForm):
    action = forms.ChoiceField(choices=ACTION_CHOICES)

    class Meta:
        model = models.ModerationItem
        fields = ()
