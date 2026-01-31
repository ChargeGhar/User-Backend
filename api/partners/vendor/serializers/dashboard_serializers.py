"""
Vendor Dashboard Serializers
"""

from rest_framework import serializers


class VendorStationInfoSerializer(serializers.Serializer):
    """Vendor's assigned station info"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()


class VendorRevenueStatsSerializer(serializers.Serializer):
    """Revenue statistics for a time period"""
    transactions = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    my_share = serializers.DecimalField(max_digits=10, decimal_places=2)


class VendorDashboardSerializer(serializers.Serializer):
    """Vendor dashboard response"""
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_payout = serializers.DecimalField(max_digits=10, decimal_places=2)
    station = VendorStationInfoSerializer(allow_null=True)
    today = VendorRevenueStatsSerializer()
    this_week = VendorRevenueStatsSerializer()
    this_month = VendorRevenueStatsSerializer()
