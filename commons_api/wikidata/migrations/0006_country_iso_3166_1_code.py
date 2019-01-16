# Generated by Django 2.1.1 on 2018-11-19 09:55

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wikidata', '0005_seat_and_district_counts'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='iso_3166_1_code',
            field=models.CharField(blank=True, help_text='Uppercase ISO 3166-1 country code', max_length=2, null=True, validators=[django.core.validators.RegexValidator('^[A-Z]{2}$')]),
        ),
    ]
