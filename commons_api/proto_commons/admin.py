from django.contrib import admin

from . import models


class ShapefileAdmin(admin.ModelAdmin):
    list_display = ('id', 'url')


admin.site.register(models.Shapefile, ShapefileAdmin)