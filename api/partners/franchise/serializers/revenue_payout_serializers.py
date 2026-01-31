"""
Franchise Revenue & Payout Serializers
"""
from rest_framework import serializers


class RevenueStationSerializer(serializers.Serializer):
    """Station info for revenue"""
    id = serializers.UUIDField()
    station_name = serializers.CharField()
    serial_number = serializers.CharField()


class RevenueVendorSerializer(serializers.Serializer):
    """Vendor info for revenue"""
    id = serializers.UUIDField()
    code = serializers.CharField()
    business_name = serializers.CharField()


class RevenueDistributionSerializer(serializers.Serializer):
    """Revenue distribution item"""
    id = serializers.UUIDField()
    transaction_id = serializers.UUIDField()
    rental_id = serializers.UUIDField(allow_null=True)
    station = RevenueStationSerializer(allow_null=True)
    vendor = RevenueVendorSerializer(allow_null=True)
    gross_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    service_charge = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    chargeghar_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    franchise_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    vendor_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    is_distributed = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class RevenueSummarySerializer(serializers.Serializer):
    """Revenue summary"""
    total_transactions = serializers.IntegerField()
    total_gross = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_net = serializers.DecimalField(max_digits=12, decimal_places=2)
    franchise_total_share = serializers.DecimalField(max_digits=12, decimal_places=2)
