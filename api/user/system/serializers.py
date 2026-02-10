from __future__ import annotations

from rest_framework import serializers
from django.utils import timezone

from api.user.system.models import Country, AppConfig, AppVersion, AppUpdate


# ============================================================================
# Country Serializers
# ============================================================================
class CountrySerializer(serializers.ModelSerializer):
    """Serializer for Country model"""
    
    class Meta:
        model = Country
        fields = [
            'id', 'name', 'code', 'dial_code', 'flag_url', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CountryListSerializer(serializers.ModelSerializer):
    """Minimal serializer for country listing"""
    
    class Meta:
        model = Country
        fields = ['id', 'name', 'code', 'dial_code', 'flag_url']


# ============================================================================
# App Config Serializers
# ============================================================================
class AppConfigSerializer(serializers.ModelSerializer):
    """Serializer for app configs with sensitive data filtering"""
    
    class Meta:
        model = AppConfig
        fields = ['id', 'key', 'value', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppConfigAdminSerializer(serializers.ModelSerializer):
    """Admin serializer for app configs (shows sensitive data to admins)"""
    
    class Meta:
        model = AppConfig
        fields = ['id', 'key', 'value', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateAppConfigSerializer(serializers.Serializer):
    """Serializer for creating app configuration"""
    key = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Configuration key (unique identifier)"
    )
    value = serializers.JSONField(
        required=True,
        help_text="Configuration value (can be any JSON type)"
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default='',
        help_text="Description of the configuration"
    )
    is_active = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether the configuration is active"
    )


class UpdateAppConfigSerializer(serializers.Serializer):
    """Serializer for updating app configuration"""
    config_id = serializers.UUIDField(
        required=False,
        help_text="Configuration ID (use either config_id or key)"
    )
    key = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Configuration key (use either config_id or key)"
    )
    value = serializers.JSONField(
        required=False,
        help_text="New configuration value"
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="New description"
    )
    is_active = serializers.BooleanField(
        required=False,
        help_text="New active status"
    )
    
    def validate(self, data):
        """Ensure at least one of config_id or key is provided"""
        if not data.get('config_id') and not data.get('key'):
            raise serializers.ValidationError(
                "Either config_id or key must be provided"
            )
        return data


class DeleteAppConfigSerializer(serializers.Serializer):
    """Serializer for deleting app configuration"""
    config_id = serializers.UUIDField(
        required=False,
        help_text="Configuration ID (use either config_id or key)"
    )
    key = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Configuration key (use either config_id or key)"
    )
    
    def validate(self, data):
        """Ensure at least one of config_id or key is provided"""
        if not data.get('config_id') and not data.get('key'):
            raise serializers.ValidationError(
                "Either config_id or key must be provided"
            )
        return data


# ============================================================================
# App Version Serializers
# ============================================================================
class AppVersionSerializer(serializers.ModelSerializer):
    """Serializer for AppVersion model"""
    
    class Meta:
        model = AppVersion
        fields = [
            'id', 'version', 'platform', 'is_mandatory', 'download_url',
            'release_notes', 'released_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_version(self, value):
        """Validate version format"""
        import re
        version_pattern = r'^\d+\.\d+\.\d+$'  # e.g., 1.0.0
        if not re.match(version_pattern, value):
            raise serializers.ValidationError(
                "Version must be in format X.Y.Z (e.g., 1.0.0)"
            )
        return value
    
    def validate_released_at(self, value):
        """Validate release date is not in the future"""
        if value > timezone.now():
            raise serializers.ValidationError(
                "Release date cannot be in the future"
            )
        return value


class AppVersionCheckSerializer(serializers.Serializer):
    """Serializer for app version check requests"""
    platform = serializers.ChoiceField(choices=AppVersion.PLATFORM_CHOICES)
    current_version = serializers.CharField(max_length=255)
    
    def validate_current_version(self, value):
        """Validate current version format"""
        import re
        version_pattern = r'^\d+\.\d+\.\d+$'  # e.g., 1.0.0
        if not re.match(version_pattern, value):
            raise serializers.ValidationError(
                "Version must be in format X.Y.Z (e.g., 1.0.0)"
            )
        return value


class AppVersionCheckResponseSerializer(serializers.Serializer):
    """Response serializer for version check"""
    update_available = serializers.BooleanField()
    is_mandatory = serializers.BooleanField()
    latest_version = serializers.CharField()
    download_url = serializers.URLField(allow_null=True)
    release_notes = serializers.CharField(allow_null=True)
    current_version = serializers.CharField()


# ============================================================================
# App Update Serializers
# ============================================================================
class AppUpdateSerializer(serializers.ModelSerializer):
    """Serializer for AppUpdate model"""
    
    class Meta:
        model = AppUpdate
        fields = [
            'id', 'version', 'title', 'description', 'features',
            'is_major', 'released_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_features(self, value):
        """Validate features is a list of strings"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Features must be a list")
        
        for feature in value:
            if not isinstance(feature, str):
                raise serializers.ValidationError("Each feature must be a string")
        
        return value


class AppUpdateListSerializer(serializers.ModelSerializer):
    """MVP serializer for update list views - minimal fields"""
    
    class Meta:
        model = AppUpdate
        fields = ['id', 'version', 'title', 'is_major', 'released_at']
        read_only_fields = fields


# ============================================================================
# App Health Serializers
# ============================================================================
class AppHealthSerializer(serializers.Serializer):
    """MVP serializer for app health check responses"""
    
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    version = serializers.CharField()
    database = serializers.CharField()
    cache = serializers.CharField()
    celery = serializers.CharField()
    uptime_seconds = serializers.IntegerField()


# ============================================================================
# Issue Types Serializers
# ============================================================================
class IssueTypeChoiceSerializer(serializers.Serializer):
    """Single issue type choice"""
    value = serializers.CharField()
    label = serializers.CharField()


class IssueTypesResponseSerializer(serializers.Serializer):
    """Response for issue types endpoint"""
    station_issue_types = IssueTypeChoiceSerializer(many=True)
    rental_issue_types = IssueTypeChoiceSerializer(many=True)


# ============================================================================
# Partner Request Serializers
# ============================================================================

class PartnerRequestCreateSerializer(serializers.Serializer):
    """Serializer for creating partner request"""
    full_name = serializers.CharField(max_length=100)
    contact_number = serializers.CharField(max_length=20)
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate_full_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Full name must be at least 3 characters"
            )
        return value.strip()

    def validate_contact_number(self, value):
        cleaned = value.strip().replace(' ', '').replace('-', '')
        if len(cleaned) < 10:
            raise serializers.ValidationError(
                "Contact number must be at least 10 digits"
            )
        return value.strip()

    def validate_subject(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Subject must be at least 3 characters"
            )
        return value.strip()


class PartnerRequestAssignedBySerializer(serializers.Serializer):
    """Serializer for assigned_by user details"""
    id = serializers.CharField()
    username = serializers.CharField(allow_null=True)
    email = serializers.EmailField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)


class PartnerRequestDetailSerializer(serializers.Serializer):
    """Serializer for partner request detail response"""
    business_name = serializers.CharField()
    contact_phone = serializers.CharField()
    subject = serializers.CharField(allow_null=True)
    message = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    assigned_by = PartnerRequestAssignedBySerializer(allow_null=True, required=False)
    assigned_at = serializers.DateTimeField(allow_null=True, required=False)
    partner_code = serializers.CharField(allow_null=True, required=False)
    partner_type = serializers.CharField(allow_null=True, required=False)
    vendor_type = serializers.CharField(allow_null=True, required=False)
    contact_email = serializers.EmailField(allow_null=True, required=False)
    address = serializers.CharField(allow_null=True, required=False)
    upfront_amount = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    revenue_share_percent = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True, required=False)
    notes = serializers.CharField(allow_null=True, required=False)
