import json

from rest_framework.serializers import ModelSerializer

from boundaries.views import BoundaryListView
from . import models


class SpatialSerializer(ModelSerializer):
    default_geo_field = 'simple_shape'
    allowed_geo_fields = BoundaryListView.allowed_geo_fields

    @property
    def geo_field_name(self):
        geo_field = self.context['request'].GET.get('geometry',
                                                    self.default_geo_field)
        if geo_field in self.allowed_geo_fields:
            return geo_field

    @property
    def should_expose_geometry(self):
        return self.context['format'] == 'geojson' or 'geometry' in self.context['request'].GET

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.should_expose_geometry and self.geo_field_name:
            if instance.boundary_id:
                data['geometry'] = json.loads(getattr(instance.boundary, self.geo_field_name).geojson)
            else:
                data['geometry'] = None
        return data


class CountrySerializer(SpatialSerializer):
    class Meta:
        model = models.Country
        fields = ('id', 'labels', 'flag_image', 'population', 'iso_3166_1_code', 'wikipedia_articles')


class PersonSerializer(ModelSerializer):
    class Meta:
        model = models.Person
        fields = ('id', 'labels', 'facebook_id', 'twitter_id')


class ElectoralDistrictSerializer(SpatialSerializer):
    class Meta:
        model = models.ElectoralDistrict
        fields = ('id', 'labels', 'legislative_house')


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
