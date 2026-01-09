"""
PowerBank Serializers
Auto-generated for admin powerbank management
"""

from __future__ import annotations
from rest_framework import serializers
from api.user.stations.models import PowerBank


class AdminPowerBankListSerializer(serializers.Serializer):
    """Serializer for powerbank list filters"""
    status = serializers.ChoiceField(
        choices=PowerBank.POWERBANK_STATUS_CHOICES,
        required=False,
        help_text="Filter by powerbank status"
    )
    station_id = serializers.UUIDField(
        required=False,
        help_text="Filter by station ID"
    )
    search = serializers.CharField(
        required=False,
        max_length=255,
        help_text="Search by serial number or model"
    )
    min_battery = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        help_text="Minimum battery level"
    )
    max_battery = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        help_text="Maximum battery level"
    )
    page = serializers.IntegerField(
        default=1,
        min_value=1
    )
    page_size = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100
    )


class AdminPowerBankHistorySerializer(serializers.Serializer):
    """Serializer for powerbank rental history filters"""
    status = serializers.CharField(
        required=False,
        help_text="Filter by rental status"
    )
    start_date = serializers.DateTimeField(
        required=False,
        help_text="Filter rentals from this date"
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text="Filter rentals until this date"
    )
    page = serializers.IntegerField(
        default=1,
        min_value=1
    )
    page_size = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100
    )
    
    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date cannot be after end_date")
        
        return attrs


class UpdatePowerBankStatusSerializer(serializers.Serializer):
    """Serializer for updating powerbank status"""
    status = serializers.ChoiceField(
        choices=['AVAILABLE', 'MAINTENANCE', 'DAMAGED'],
        help_text="New status for the powerbank (cannot set to RENTED manually)"
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Reason for status change"
    )
