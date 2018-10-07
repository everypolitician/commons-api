from rest_framework.serializers import ModelSerializer

from . import models


class PersonSerializer(ModelSerializer):
    class Meta:
        model = models.Person
        fields = ('id', 'labels', 'facebook_id', 'twitter_id')


class ElectoralDistrictSerializer(ModelSerializer):
    class Meta:
        model = models.ElectoralDistrict
        fields = ('id', 'labels')


class AdministrativeAreaSerializer(ModelSerializer):
    class Meta:
        model = models.AdministrativeArea
        fields = ('id', 'labels')


class LegislativeHouseSerializer(ModelSerializer):
    administrative_area = AdministrativeAreaSerializer()

    class Meta:
        model = models.LegislativeHouse
        fields = ('id', 'labels', 'administrative_area')


class LegislativeMembershipSerializer(ModelSerializer):
    person = PersonSerializer()
    district = ElectoralDistrictSerializer()
    legislative_house = LegislativeHouseSerializer()

    class Meta:
        model = models.LegislativeMembership
        fields = ('id', 'person', 'legislative_house', 'legislative_house_id', 'district', 'district_id', 'start', 'end')
