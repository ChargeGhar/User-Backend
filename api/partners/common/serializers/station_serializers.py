"""
Partner Station Serializers (Common for both Franchise and Vendor)
"""
from rest_framework import serializers


class PartnerBasicSerializer(serializers.Serializer):
    """Partner basic info for station list"""
    id = serializers.UUIDField()
    code = serializers.CharField()
    business_name = serializers.CharField()
    partner_type = serializers.CharField()
    vendor_type = serializers.CharField(allow_null=True)
    status = serializers.CharField()


class StationDistributionSerializer(serializers.Serializer):
    """Distribution info"""
    id = serializers.UUIDField()
    distribution_type = serializers.CharField()
    effective_date = serializers.DateField()
    is_active = serializers.BooleanField()


class StationRevenueStatsSerializer(serializers.Serializer):
    """Revenue statistics"""
    today_transactions = serializers.IntegerField()
    today_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    this_month_transactions = serializers.IntegerField()
    this_month_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class PartnerStationListSerializer(serializers.Serializer):
    """Station list item for partners"""
    id = serializers.UUIDField()
    station_name = serializers.CharField()
    serial_number = serializers.CharField()
    imei = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=17, decimal_places=15)
    longitude = serializers.DecimalField(max_digits=18, decimal_places=15)
    address = serializers.CharField()
    landmark = serializers.CharField(allow_null=True)
    total_slots = serializers.IntegerField()
    status = serializers.CharField()
    is_maintenance = serializers.BooleanField()
    last_heartbeat = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    amenities = serializers.ListField(child=serializers.CharField())
    available_slots = serializers.IntegerField()
    occupied_slots = serializers.IntegerField()
    total_powerbanks = serializers.IntegerField()
    available_powerbanks = serializers.IntegerField()
    distribution = StationDistributionSerializer()
    assigned_partner = PartnerBasicSerializer(allow_null=True)
    revenue_stats = StationRevenueStatsSerializer()
