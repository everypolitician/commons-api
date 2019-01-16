from django.contrib import admin

from . import models


class CountryAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'iso_3166_1_code')


class LegislativeHouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'country', 'number_of_seats', 'number_of_districts')
    list_filter = ('country',)


class AdministrativeAreaAdmin(admin.ModelAdmin):
    list_display = ('id', 'label')


class LegislativeTermAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'start', 'end')


class LegislativeMembershipAdmin(admin.ModelAdmin):
    list_display = ('id', 'person', 'legislative_house', 'district', 'parliamentary_group', 'start', 'end')
    list_filter = ('end_cause', 'subject_has_role', 'parliamentary_group')


class PersonAdmin(admin.ModelAdmin):
    list_display = ('id', 'label')


class TermAdmin(admin.ModelAdmin):
    list_display = ('id', 'label')


class ModerationItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_type', 'creation', 'deletion')
    list_filter = ('content_type', 'creation', 'deletion')


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'label')


class ElectoralDistrictAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'legislative_house')
    list_filter = ('legislative_house',)


admin.site.register(models.Country, CountryAdmin)
admin.site.register(models.LegislativeHouse, LegislativeHouseAdmin)
admin.site.register(models.AdministrativeArea, AdministrativeAreaAdmin)
admin.site.register(models.LegislativeTerm, LegislativeTermAdmin)
admin.site.register(models.LegislativeMembership, LegislativeMembershipAdmin)
admin.site.register(models.Person, PersonAdmin)
admin.site.register(models.Term, TermAdmin)
admin.site.register(models.ModerationItem, ModerationItemAdmin)
admin.site.register(models.Organization, OrganizationAdmin)
admin.site.register(models.ElectoralDistrict, ElectoralDistrictAdmin)