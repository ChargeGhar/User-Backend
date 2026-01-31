"""
Vendor Revenue Serializers
"""

from rest_framework import serializers


class VendorRevenueStationSerializer(serializers.Serializer):
    """Station info in revenue transaction"""
    id = serializers.UUIDField()
    name = serializers.CharField()


class VendorRevenueTransactionSerializer(serializers.Serializer):
    """Single revenue transaction"""
    id = serializers.UUIDField()
    rental_id = serializers.UUIDField()
    transaction_date = serializers.DateTimeField()
    gross_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    vat_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    service_charge = serializers.DecimalField(max_digits=10, decimal_places=2)
    vendor_share = serializers.DecimalField(max_digits=10, decimal_places=2)
    vendor_share_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    station = VendorRevenueStationSerializer(allow_null=True)


class VendorRevenueSummarySerializer(serializers.Serializer):
    """Revenue summary statistics"""
    total_transactions = serializers.IntegerField()
    total_gross_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_net_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_vendor_share = serializers.DecimalField(max_digits=10, decimal_places=2)


class VendorRevenueListSerializer(serializers.Serializer):
    """Paginated revenue list response"""
    results = VendorRevenueTransactionSerializer(many=True)
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    summary = VendorRevenueSummarySerializer()
