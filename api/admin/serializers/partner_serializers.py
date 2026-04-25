# api/admin/serializers/partner_serializers.py
"""
Admin Partner Serializers

Serializers for admin partner management endpoints.
Based on Endpoints.md Section 1.1-1.5
"""
from __future__ import annotations

from rest_framework import serializers
from decimal import Decimal


# ============================================================================
# Filter Serializers
# ============================================================================

class AdminPartnerListFilterSerializer(serializers.Serializer):
    """Filter serializer for partner list endpoint"""
    partner_type = serializers.ChoiceField(
        choices=['FRANCHISE', 'VENDOR'],
        required=False,
        help_text="Filter by partner type"
    )
    vendor_type = serializers.ChoiceField(
        choices=['REVENUE', 'NON_REVENUE'],
        required=False,
        help_text="Filter by vendor type (only for VENDOR partner_type)"
    )
    status = serializers.ChoiceField(
        choices=['PENDING', 'ACTIVE', 'INACTIVE', 'SUSPENDED'],
        required=False,
        help_text="Filter by status"
    )
    parent_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Filter by parent (franchise) ID. Empty string for ChargeGhar-level"
    )
    search = serializers.CharField(
        required=False,
        help_text="Search by name, code, phone, or email"
    )
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class AdminStationDistributionFilterSerializer(serializers.Serializer):
    """Filter serializer for station distribution list"""
    station_id = serializers.UUIDField(required=False)
    partner_id = serializers.UUIDField(required=False)
    distribution_type = serializers.ChoiceField(
        choices=['CHARGEGHAR_TO_FRANCHISE', 'CHARGEGHAR_TO_VENDOR', 'FRANCHISE_TO_VENDOR'],
        required=False
    )
    is_active = serializers.BooleanField(required=False, allow_null=True, default=True)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


# ============================================================================
# Response Serializers
# ============================================================================

class AdminPartnerSerializer(serializers.Serializer):
    """Serializer for partner list response"""
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(read_only=True)
    partner_type = serializers.CharField(read_only=True)
    vendor_type = serializers.CharField(read_only=True, allow_null=True)
    business_name = serializers.CharField(read_only=True)
    contact_phone = serializers.CharField(read_only=True)
    contact_email = serializers.EmailField(read_only=True, allow_null=True)
    subject = serializers.CharField(read_only=True, allow_null=True)
    message = serializers.CharField(read_only=True, allow_null=True)
    status = serializers.CharField(read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    # Parent info
    parent_id = serializers.UUIDField(source='parent.id', read_only=True, allow_null=True)
    parent_name = serializers.CharField(source='parent.business_name', read_only=True, allow_null=True)

    # User info
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)


class AdminPartnerDetailSerializer(AdminPartnerSerializer):
    """Detailed serializer for single partner view"""
    address = serializers.CharField(read_only=True, allow_null=True)
    upfront_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    revenue_share_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True, allow_null=True
    )
    assigned_at = serializers.DateTimeField(read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.username', read_only=True, allow_null=True)
    notes = serializers.CharField(read_only=True, allow_null=True)
    updated_at = serializers.DateTimeField(read_only=True)

    # Computed fields
    stations_count = serializers.SerializerMethodField()
    vendors_count = serializers.SerializerMethodField()

    def get_stations_count(self, obj):
        """Get count of stations assigned to this partner"""
        from api.partners.common.models import StationDistribution
        return StationDistribution.objects.filter(
            partner=obj,
            is_active=True
        ).count()

    def get_vendors_count(self, obj):
        """Get count of vendors under this partner (for franchises)"""
        if obj.partner_type == 'FRANCHISE':
            return obj.child_partners.filter(status='ACTIVE').count()
        return 0


class AdminStationDistributionSerializer(serializers.Serializer):
    """Serializer for station distribution response"""
    id = serializers.UUIDField(read_only=True)
    station_id = serializers.UUIDField(read_only=True)
    station_name = serializers.CharField(source='station.station_name', read_only=True)
    station_code = serializers.CharField(source='station.serial_number', read_only=True)
    partner_id = serializers.UUIDField(read_only=True)
    partner_name = serializers.CharField(source='partner.business_name', read_only=True)
    partner_code = serializers.CharField(source='partner.code', read_only=True)
    distribution_type = serializers.CharField(read_only=True)
    effective_date = serializers.DateField(read_only=True)
    expiry_date = serializers.DateField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class AdminStationRevenueShareSerializer(serializers.Serializer):
    """Serializer for station revenue share response"""
    id = serializers.UUIDField(read_only=True)
    distribution_id = serializers.UUIDField(read_only=True)
    revenue_model = serializers.CharField(read_only=True)
    partner_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True, allow_null=True
    )
    fixed_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, allow_null=True
    )


# ============================================================================
# Create/Update Serializers
# ============================================================================

class CreateFranchiseSerializer(serializers.Serializer):
    """Serializer for creating a franchise partner"""
    user_id = serializers.IntegerField(
        help_text="Existing user ID to link as partner"
    )
    business_name = serializers.CharField(max_length=100)
    contact_phone = serializers.CharField(max_length=20)
    contact_email = serializers.EmailField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True)
    upfront_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'),
        help_text="One-time upfront payment received"
    )
    revenue_share_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        min_value=Decimal('0'), max_value=Decimal('100'),
        help_text="Franchise's % share of station net revenue (y%)"
    )
    station_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        help_text="List of station UUIDs to assign to franchise"
    )
    password = serializers.CharField(
        write_only=True, min_length=8, max_length=128,
        help_text="Initial password for partner login"
    )
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate_user_id(self, value):
        """Validate user exists and is not already a partner"""
        from api.user.auth.models import User
        from api.partners.common.repositories import PartnerRepository
        from api.partners.common.models import Partner

        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        existing_partner = PartnerRepository.get_by_user_id(value)
        if existing_partner and existing_partner.status != Partner.Status.PENDING:
            raise serializers.ValidationError("User is already a partner")

        return value

    def validate_station_ids(self, value):
        """Validate stations exist and are not already assigned"""
        if not value:
            return value

        # Check for duplicates
        if len(value) != len(set(str(s) for s in value)):
            raise serializers.ValidationError("Duplicate station IDs are not allowed.")

        from api.user.stations.models import Station
        from api.partners.common.repositories import StationDistributionRepository

        for station_id in value:
            # Check station exists
            if not Station.objects.filter(id=station_id).exists():
                raise serializers.ValidationError(f"Station {station_id} not found")

            # Check station not already assigned
            existing = StationDistributionRepository.get_active_by_station(str(station_id))
            if existing.exists():
                raise serializers.ValidationError(
                    f"Station {station_id} is already assigned to another partner"
                )

        return value


class CreateVendorSerializer(serializers.Serializer):
    """Serializer for creating a vendor partner (ChargeGhar-level)"""
    user_id = serializers.IntegerField(
        help_text="Existing user ID to link as partner"
    )
    vendor_type = serializers.ChoiceField(
        choices=['REVENUE', 'NON_REVENUE'],
        help_text="REVENUE vendors have dashboard access and earnings"
    )
    business_name = serializers.CharField(max_length=100)
    contact_phone = serializers.CharField(max_length=20)
    contact_email = serializers.EmailField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True)
    station_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        min_length=1,
        help_text="List of station UUIDs to assign to vendor"
    )
    # Revenue model fields (required for REVENUE vendors)
    revenue_model = serializers.ChoiceField(
        choices=['PERCENTAGE', 'FIXED'],
        required=False,
        help_text="Revenue model type (required for REVENUE vendors)"
    )
    partner_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        min_value=Decimal('0'), max_value=Decimal('100'),
        required=False, allow_null=True,
        help_text="Vendor's % share (required if revenue_model=PERCENTAGE)"
    )
    fixed_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        min_value=Decimal('0'),
        required=False, allow_null=True,
        help_text="Fixed monthly amount (required if revenue_model=FIXED)"
    )
    password = serializers.CharField(
        write_only=True, min_length=8, max_length=128,
        required=False, allow_null=True,
        help_text="Initial password (required for REVENUE vendors)"
    )
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate_user_id(self, value):
        """Validate user exists and is not already a partner"""
        from api.user.auth.models import User
        from api.partners.common.repositories import PartnerRepository
        from api.partners.common.models import Partner

        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        existing_partner = PartnerRepository.get_by_user_id(value)
        if existing_partner and existing_partner.status != Partner.Status.PENDING:
            raise serializers.ValidationError("User is already a partner")

        return value

    def validate_station_ids(self, value):
        """Validate all stations exist and are available for vendor assignment"""
        # Check for duplicates
        if len(value) != len(set(str(s) for s in value)):
            raise serializers.ValidationError("Duplicate station IDs are not allowed.")

        from api.user.stations.models import Station
        from api.partners.common.repositories import StationDistributionRepository

        for station_id in value:
            # Check station exists
            if not Station.objects.filter(id=station_id).exists():
                raise serializers.ValidationError(f"Station {station_id} not found")

            # Check station doesn't already have a vendor operator
            if StationDistributionRepository.station_has_operator(str(station_id)):
                raise serializers.ValidationError(
                    f"Station {station_id} already has an operator assigned"
                )

        return value

    def validate(self, data):
        """Cross-field validation"""
        vendor_type = data.get('vendor_type')
        revenue_model = data.get('revenue_model')
        partner_percent = data.get('partner_percent')
        fixed_amount = data.get('fixed_amount')
        password = data.get('password')

        if vendor_type == 'REVENUE':
            # REVENUE vendors require revenue model
            if not revenue_model:
                raise serializers.ValidationError({
                    "revenue_model": "Revenue model is required for REVENUE vendors"
                })

            if revenue_model == 'PERCENTAGE' and partner_percent is None:
                raise serializers.ValidationError({
                    "partner_percent": "Partner percent is required for PERCENTAGE model"
                })

            if revenue_model == 'FIXED' and fixed_amount is None:
                raise serializers.ValidationError({
                    "fixed_amount": "Fixed amount is required for FIXED model"
                })

            # REVENUE vendors need password for dashboard access
            if not password:
                raise serializers.ValidationError({
                    "password": "Password is required for REVENUE vendors (dashboard access)"
                })

        return data


class AssignStationsToVendorSerializer(serializers.Serializer):
    """Serializer for assigning additional stations to an existing vendor"""
    vendor_id = serializers.UUIDField(
        help_text="Vendor partner UUID"
    )
    station_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        min_length=1,
        help_text="List of station UUIDs to assign to the vendor"
    )
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate_vendor_id(self, value):
        """Validate vendor exists and is a VENDOR type"""
        from api.partners.common.repositories import PartnerRepository
        from api.partners.common.models import Partner

        partner = PartnerRepository.get_by_id(str(value))
        if not partner:
            raise serializers.ValidationError("Vendor not found")

        if partner.partner_type != Partner.PartnerType.VENDOR:
            raise serializers.ValidationError("Partner is not a vendor")

        return value

    def validate_station_ids(self, value):
        """Validate all stations exist and are available"""
        # Check for duplicates
        if len(value) != len(set(str(s) for s in value)):
            raise serializers.ValidationError("Duplicate station IDs are not allowed.")

        from api.user.stations.models import Station
        from api.partners.common.repositories import StationDistributionRepository

        for station_id in value:
            # Check station exists
            if not Station.objects.filter(id=station_id).exists():
                raise serializers.ValidationError(f"Station {station_id} not found")

            # Check station doesn't already have a vendor operator
            if StationDistributionRepository.station_has_operator(str(station_id)):
                raise serializers.ValidationError(
                    f"Station {station_id} already has an operator assigned"
                )

        return value


class UpdatePartnerSerializer(serializers.Serializer):
    """Serializer for updating partner details"""
    business_name = serializers.CharField(max_length=100, required=False)
    contact_phone = serializers.CharField(max_length=20, required=False)
    contact_email = serializers.EmailField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    subject = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    message = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    # Franchise-specific
    upfront_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    revenue_share_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        min_value=Decimal('0'), max_value=Decimal('100'),
        required=False, allow_null=True
    )


class UpdatePartnerStatusSerializer(serializers.Serializer):
    """Serializer for updating partner status"""
    status = serializers.ChoiceField(
        choices=['PENDING', 'ACTIVE', 'INACTIVE', 'SUSPENDED'],
        help_text="New status for partner"
    )
    reason = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Reason for status change (added to notes)"
    )


# ============================================================================
# Payout Serializers
# ============================================================================

class AdminPayoutListFilterSerializer(serializers.Serializer):
    """Filter serializer for payout list"""
    payout_type = serializers.ChoiceField(
        choices=['CHARGEGHAR_TO_FRANCHISE', 'CHARGEGHAR_TO_VENDOR', 'FRANCHISE_TO_VENDOR'],
        required=False
    )
    status = serializers.ChoiceField(
        choices=['PENDING', 'APPROVED', 'PROCESSING', 'COMPLETED', 'REJECTED'],
        required=False
    )
    partner_id = serializers.UUIDField(required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class AdminPayoutSerializer(serializers.Serializer):
    """Serializer for payout response"""
    id = serializers.UUIDField(read_only=True)
    partner_id = serializers.UUIDField(read_only=True)
    partner_name = serializers.CharField(source='partner.business_name', read_only=True)
    partner_code = serializers.CharField(source='partner.code', read_only=True)
    payout_type = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    bank_name = serializers.CharField(read_only=True, allow_null=True)
    account_number = serializers.CharField(read_only=True, allow_null=True)
    account_holder_name = serializers.CharField(read_only=True, allow_null=True)
    status = serializers.CharField(read_only=True)
    reference_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    processed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    processed_by_name = serializers.CharField(
        source='processed_by.username', read_only=True, allow_null=True
    )


class AdminPayoutDetailSerializer(AdminPayoutSerializer):
    """Detailed serializer for single payout view"""
    vat_deducted = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    service_charge_deducted = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    rejection_reason = serializers.CharField(read_only=True, allow_null=True)
    admin_notes = serializers.CharField(read_only=True, allow_null=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AdminPayoutActionSerializer(serializers.Serializer):
    """Serializer for payout actions (approve/reject/complete)"""
    admin_notes = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Admin notes for this action"
    )


class AdminPayoutRejectSerializer(serializers.Serializer):
    """Serializer for rejecting a payout"""
    rejection_reason = serializers.CharField(
        required=True,
        help_text="Reason for rejection"
    )
    admin_notes = serializers.CharField(required=False, allow_blank=True)


# ============================================================================
# Password Management Serializers
# ============================================================================

class AdminResetPartnerPasswordSerializer(serializers.Serializer):
    """Serializer for admin resetting a partner's password"""
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        help_text="New password for the partner (min 8 chars)"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        help_text="Confirm new password"
    )

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match"
            })
        return data


# ============================================================================
# Vendor Type Change Serializer
# ============================================================================

class ChangeVendorTypeSerializer(serializers.Serializer):
    """
    Serializer for changing vendor type (NON_REVENUE <-> REVENUE).

    When changing to REVENUE:
    - password is required (for dashboard access)
    - revenue_model is required
    - partner_percent or fixed_amount is required based on revenue_model

    When changing to NON_REVENUE:
    - No additional fields required
    - Revenue share will be deleted
    """
    vendor_type = serializers.ChoiceField(
        choices=['REVENUE', 'NON_REVENUE'],
        help_text="New vendor type"
    )
    # Required when changing to REVENUE
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        required=False,
        allow_null=True,
        help_text="Password for dashboard access (required when changing to REVENUE)"
    )
    revenue_model = serializers.ChoiceField(
        choices=['PERCENTAGE', 'FIXED'],
        required=False,
        allow_null=True,
        help_text="Revenue model type (required when changing to REVENUE)"
    )
    partner_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
        max_value=Decimal('100'),
        required=False,
        allow_null=True,
        help_text="Vendor's % share (required if revenue_model=PERCENTAGE)"
    )
    fixed_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
        allow_null=True,
        help_text="Fixed monthly amount (required if revenue_model=FIXED)"
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Reason for vendor type change (added to notes)"
    )

    def validate(self, data):
        vendor_type = data.get('vendor_type')

        if vendor_type == 'REVENUE':
            # Validate required fields for REVENUE
            if not data.get('password'):
                raise serializers.ValidationError({
                    "password": "Password is required when changing to REVENUE vendor"
                })

            if not data.get('revenue_model'):
                raise serializers.ValidationError({
                    "revenue_model": "Revenue model is required when changing to REVENUE vendor"
                })

            revenue_model = data.get('revenue_model')
            if revenue_model == 'PERCENTAGE' and data.get('partner_percent') is None:
                raise serializers.ValidationError({
                    "partner_percent": "Partner percent is required for PERCENTAGE model"
                })

            if revenue_model == 'FIXED' and data.get('fixed_amount') is None:
                raise serializers.ValidationError({
                    "fixed_amount": "Fixed amount is required for FIXED model"
                })

        return data
