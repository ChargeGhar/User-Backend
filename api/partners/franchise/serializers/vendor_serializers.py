"""
Franchise Vendor Serializers
"""
from rest_framework import serializers


class VendorStationSerializer(serializers.Serializer):
    """Station info for vendor list"""
    id = serializers.UUIDField()
    station_name = serializers.CharField()
    serial_number = serializers.CharField()
    address = serializers.CharField()
    status = serializers.CharField()


class FranchiseVendorListSerializer(serializers.Serializer):
    """Vendor list item for franchise (updated for multi-station)"""
    id = serializers.UUIDField()
    code = serializers.CharField()
    business_name = serializers.CharField()
    vendor_type = serializers.CharField()
    contact_phone = serializers.CharField()
    contact_email = serializers.EmailField(allow_null=True)
    status = serializers.CharField()
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    created_at = serializers.DateTimeField()
    stations = VendorStationSerializer(many=True, allow_null=True)
    station_count = serializers.IntegerField(default=0)


class CreateVendorSerializer(serializers.Serializer):
    """Create vendor request (updated for multi-station)"""
    user_id = serializers.IntegerField(required=True, help_text="Existing user ID to link as vendor")
    vendor_type = serializers.ChoiceField(
        choices=['REVENUE', 'NON_REVENUE'],
        required=True,
        help_text="REVENUE vendors have dashboard access and earnings"
    )
    business_name = serializers.CharField(required=True, max_length=100)
    contact_phone = serializers.CharField(required=True, max_length=20)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    station_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        min_length=1,
        help_text="List of station UUIDs to assign to vendor"
    )
    revenue_model = serializers.ChoiceField(
        choices=['PERCENTAGE', 'FIXED'],
        required=False,
        allow_null=True,
        help_text="Revenue model type (required for REVENUE vendors)"
    )
    partner_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Vendor's % share (required if revenue_model=PERCENTAGE)"
    )
    fixed_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Fixed monthly amount (required if revenue_model=FIXED)"
    )
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="Initial password (required for REVENUE vendors)"
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_station_ids(self, value):
        """Validate station IDs - no duplicates"""
        if len(value) != len(set(str(s) for s in value)):
            raise serializers.ValidationError("Duplicate station IDs are not allowed.")
        return value


class UpdateVendorSerializer(serializers.Serializer):
    """Update vendor request"""
    business_name = serializers.CharField(required=False, max_length=100)
    contact_phone = serializers.CharField(required=False, max_length=20)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class UpdateVendorStatusSerializer(serializers.Serializer):
    """Update vendor status request"""
    status = serializers.ChoiceField(
        choices=['ACTIVE', 'INACTIVE', 'SUSPENDED'],
        required=True
    )
    reason = serializers.CharField(required=False, allow_blank=True)
