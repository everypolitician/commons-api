# Generated by Django 2.1.1 on 2018-10-16 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wikidata', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='legislativeterm',
            name='series_ordinal',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
