from django.contrib import admin

from . import models


class CountryAdmin(admin.ModelAdmin):
    list_display = ('id', 'label')


class LegislativeHouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'country')
    list_filter = ('country',)


class AdministrativeAreaAdmin(admin.ModelAdmin):
    list_display = ('id', 'label')


class LegislativeTermAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'start', 'end')


class LegislativeMembershipAdmin(admin.ModelAdmin):
    list_display = ('id', 'person', 'legislative_house', 'district', 'start', 'end')
    list_filter = ('end_cause', 'subject_has_role')


class PersonAdmin(admin.ModelAdmin):
    list_display = ('id', 'label')


class TermAdmin(admin.ModelAdmin):
    list_display = ('id', 'label')


class ModerationItemAdmin(admin.ModelAdmin):
    list_display = ('id',)


admin.site.register(models.Country, CountryAdmin)
admin.site.register(models.LegislativeHouse, LegislativeHouseAdmin)
admin.site.register(models.AdministrativeArea, AdministrativeAreaAdmin)
admin.site.register(models.LegislativeTerm, LegislativeTermAdmin)
admin.site.register(models.LegislativeMembership, LegislativeMembershipAdmin)
admin.site.register(models.Person, PersonAdmin)
admin.site.register(models.Term, TermAdmin)
admin.site.register(models.ModerationItem, ModerationItemAdmin)