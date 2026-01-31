"""
Admin Revenue Serializers
"""

from rest_framework import serializers


class AdminRevenueItemSerializer(serializers.Serializer):
    """Admin revenue item - flat, readable structure"""
    # Revenue Distribution Core
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    
    # Financial Breakdown
    gross_amount = serializers.CharField()
    vat_amount = serializers.CharField()
    service_charge = serializers.CharField()
    net_amount = serializers.CharField()
    chargeghar_share = serializers.CharField()
    franchise_share = serializers.CharField()
    vendor_share = serializers.CharField()
    
    # Distribution Status
    is_distributed = serializers.BooleanField()
    distributed_at = serializers.DateTimeField(allow_null=True)
    
    # Transaction (Related)
    transaction_id = serializers.CharField()
    transaction_status = serializers.CharField()
    payment_method = serializers.CharField()
    user_email = serializers.EmailField(allow_null=True)
    
    # Rental (Related - nullable)
    rental_code = serializers.CharField(allow_null=True)
    rental_status = serializers.CharField(allow_null=True)
    started_at = serializers.DateTimeField(allow_null=True)
    ended_at = serializers.DateTimeField(allow_null=True)
    
    # Station (Related)
    station_name = serializers.CharField()
    station_sn = serializers.CharField()
    
    # Partners (Related - nullable)
    franchise_code = serializers.CharField(allow_null=True)
    franchise_name = serializers.CharField(allow_null=True)
    vendor_code = serializers.CharField(allow_null=True)
    vendor_name = serializers.CharField(allow_null=True)
    
    # Audit Trail
    is_reversal = serializers.BooleanField()
    reversal_reason = serializers.CharField(allow_null=True)


class AdminRevenueSummarySerializer(serializers.Serializer):
    """Revenue summary statistics"""
    total_transactions = serializers.IntegerField()
    total_gross = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_vat = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_service_charge = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_net = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_chargeghar_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_franchise_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_vendor_share = serializers.DecimalField(max_digits=12, decimal_places=2)
