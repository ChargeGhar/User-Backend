"""
Franchise Agreement Serializers
"""

from rest_framework import serializers


class VendorAgreementSerializer(serializers.Serializer):
    """Vendor agreement details"""
    
    vendor_id = serializers.UUIDField()
    vendor_code = serializers.CharField()
    vendor_name = serializers.CharField()
    vendor_type = serializers.CharField()
    station_id = serializers.UUIDField(allow_null=True)
    station_name = serializers.CharField(allow_null=True)
    station_code = serializers.CharField(allow_null=True)
    revenue_model = serializers.CharField(allow_null=True)
    partner_percent = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    fixed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class FranchiseAgreementSerializer(serializers.Serializer):
    """Franchise agreement with ChargeGhar"""
    
    franchise_id = serializers.UUIDField()
    franchise_code = serializers.CharField()
    franchise_name = serializers.CharField()
    revenue_share_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    upfront_payment = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_stations = serializers.IntegerField()
    total_vendors = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class AgreementsResponseSerializer(serializers.Serializer):
    """Complete agreements response"""
    
    franchise_agreement = FranchiseAgreementSerializer()
    vendor_agreements = VendorAgreementSerializer(many=True)
