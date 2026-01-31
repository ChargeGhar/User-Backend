"""
Franchise Dashboard Serializers

Response serializers for franchise dashboard endpoint.
"""

from rest_framework import serializers


class FranchiseProfileSerializer(serializers.Serializer):
    """Franchise profile data for dashboard"""
    
    id = serializers.UUIDField()
    code = serializers.CharField()
    business_name = serializers.CharField()
    status = serializers.CharField()
    revenue_share_percent = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2,
        allow_null=True
    )


class PeriodStatsSerializer(serializers.Serializer):
    """Revenue stats for a time period"""
    
    transactions = serializers.IntegerField()
    gross_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    my_share = serializers.DecimalField(max_digits=12, decimal_places=2)


class FranchiseDashboardSerializer(serializers.Serializer):
    """Complete franchise dashboard response"""
    
    profile = FranchiseProfileSerializer()
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_payout = serializers.DecimalField(max_digits=12, decimal_places=2)
    stations_count = serializers.IntegerField()
    vendors_count = serializers.IntegerField()
    vendor_payouts_pending = serializers.IntegerField()
    vendor_payouts_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    today = PeriodStatsSerializer()
    this_week = PeriodStatsSerializer()
    this_month = PeriodStatsSerializer()
