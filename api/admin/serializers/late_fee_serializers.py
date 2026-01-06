from __future__ import annotations
from decimal import Decimal
from rest_framework import serializers
from api.rentals.models.late_fee import LateFeeConfiguration

class LateFeeConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for Late Fee Configuration listing and detail"""
    
    fee_type_display = serializers.CharField(source='get_fee_type_display', read_only=True)
    description_text = serializers.SerializerMethodField()
    
    class Meta:
        model = LateFeeConfiguration
        fields = [
            'id',
            'name',
            'fee_type',
            'fee_type_display',
            'multiplier',
            'flat_rate_per_hour',
            'grace_period_minutes',
            'max_daily_rate',
            'is_active',
            'applicable_package_types',
            'metadata',
            'description_text',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'fee_type_display', 'description_text']
    
    def get_description_text(self, obj) -> str:
        """Get human-readable description of the fee structure"""
        return obj.get_description()


class CreateLateFeeConfigurationSerializer(serializers.Serializer):
    """Serializer for creating a new late fee configuration"""
    
    name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Clear name for this fee setting (e.g., 'Standard Late Fee')"
    )
    
    fee_type = serializers.ChoiceField(
        choices=LateFeeConfiguration.FEE_TYPE_CHOICES,
        default='MULTIPLIER',
        help_text="Fee calculation method: MULTIPLIER, FLAT_RATE, or COMPOUND"
    )
    
    multiplier = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.0'),
        required=False,
        help_text="Multiplier for MULTIPLIER or COMPOUND types (e.g., 2.0 for 2x rate)"
    )
    
    flat_rate_per_hour = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        required=False,
        help_text="Flat rate per overdue hour (NPR) for FLAT_RATE or COMPOUND types"
    )
    
    grace_period_minutes = serializers.IntegerField(
        default=0,
        required=False,
        min_value=0,
        help_text="Minutes before late charges start (0 = immediate)"
    )
    
    max_daily_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Maximum late fee per day (NPR) - leave empty for no limit"
    )
    
    is_active = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Whether this configuration is currently active"
    )
    
    applicable_package_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Limit to specific package types (empty = all packages)"
    )
    
    metadata = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Additional metadata for this configuration"
    )
    
    def validate(self, data):
        """Validate late fee configuration data"""
        fee_type = data.get('fee_type')
        multiplier = data.get('multiplier', Decimal('2.0'))
        flat_rate = data.get('flat_rate_per_hour', Decimal('0'))
        
        if fee_type == 'MULTIPLIER' and multiplier <= 0:
            raise serializers.ValidationError({'multiplier': 'Multiplier must be greater than 0'})
        elif fee_type == 'FLAT_RATE' and flat_rate <= 0:
            raise serializers.ValidationError({'flat_rate_per_hour': 'Flat rate must be greater than 0'})
        elif fee_type == 'COMPOUND' and (multiplier <= 0 or flat_rate <= 0):
            raise serializers.ValidationError('Both multiplier and flat rate must be greater than 0 for COMPOUND')
        
        return data


class UpdateLateFeeConfigurationSerializer(serializers.Serializer):
    """Serializer for updating an existing late fee configuration"""
    
    name = serializers.CharField(max_length=100, required=False)
    fee_type = serializers.ChoiceField(choices=LateFeeConfiguration.FEE_TYPE_CHOICES, required=False)
    multiplier = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    flat_rate_per_hour = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    grace_period_minutes = serializers.IntegerField(required=False, min_value=0)
    max_daily_rate = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)
    applicable_package_types = serializers.ListField(child=serializers.CharField(), required=False)
    metadata = serializers.JSONField(required=False)


class ActivateLateFeeConfigurationSerializer(serializers.Serializer):
    """Serializer for activating a late fee configuration"""
    deactivate_others = serializers.BooleanField(default=True, required=False)


class LateFeeCalculationTestSerializer(serializers.Serializer):
    """Serializer for testing late fee calculation"""
    configuration_id = serializers.UUIDField(required=True)
    normal_rate_per_minute = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    overdue_minutes = serializers.IntegerField(required=True, min_value=0)
