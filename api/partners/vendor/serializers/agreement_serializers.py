"""
Vendor Agreement Serializers
"""

from rest_framework import serializers


class VendorAgreementVendorSerializer(serializers.Serializer):
    """Vendor info"""
    id = serializers.UUIDField()
    code = serializers.CharField()
    business_name = serializers.CharField()
    vendor_type = serializers.CharField()
    status = serializers.CharField()
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)


class VendorAgreementParentSerializer(serializers.Serializer):
    """Parent info"""
    id = serializers.UUIDField()
    code = serializers.CharField()
    business_name = serializers.CharField()
    partner_type = serializers.CharField()


class VendorAgreementStationSerializer(serializers.Serializer):
    """Station info"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()
    address = serializers.CharField()
    total_slots = serializers.IntegerField()


class VendorAgreementDistributionSerializer(serializers.Serializer):
    """Distribution info"""
    distribution_type = serializers.CharField()
    effective_date = serializers.DateField()
    is_active = serializers.BooleanField()


class VendorAgreementRevenueModelSerializer(serializers.Serializer):
    """Revenue model"""
    model_type = serializers.CharField()
    partner_percent = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    fixed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    description = serializers.CharField()


class VendorAgreementSerializer(serializers.Serializer):
    """Complete agreement"""
    vendor = VendorAgreementVendorSerializer()
    parent = VendorAgreementParentSerializer(allow_null=True)
    station = VendorAgreementStationSerializer()
    distribution = VendorAgreementDistributionSerializer()
    revenue_model = VendorAgreementRevenueModelSerializer()
