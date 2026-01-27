"""
Rental Detail Serializers
=========================

Complete serializers for single item views with full data.
"""
from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field

from api.user.rentals.models import (
    Rental, 
    RentalExtension, 
    RentalIssue, 
    RentalLocation
)


class RentalDetailSerializer(serializers.ModelSerializer):
    """
    Complete serializer for rental details.
    Used in: Active rental, Start rental, Cancel rental responses
    """
    station_name = serializers.CharField(source='station.station_name', read_only=True)
    return_station_name = serializers.CharField(source='return_station.station_name', read_only=True)
    package_name = serializers.CharField(source='package.name', read_only=True)
    power_bank_serial = serializers.CharField(source='power_bank.serial_number', read_only=True)

    station_location = serializers.SerializerMethodField()
    return_station_location = serializers.SerializerMethodField()
    
    formatted_amount_paid = serializers.SerializerMethodField()
    formatted_overdue_amount = serializers.SerializerMethodField()
    duration_used = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    current_overdue_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
        help_text="Current overdue amount (realtime)"
    )
    estimated_total_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
        help_text="Estimated total cost including current overdue"
    )
    minutes_overdue = serializers.IntegerField(
        read_only=True, help_text="Current minutes overdue (realtime)"
    )
    formatted_current_overdue = serializers.SerializerMethodField()
    formatted_estimated_total = serializers.SerializerMethodField()
    
    class Meta:
        model = Rental
        fields = [
            'id', 'rental_code', 'status', 'payment_status',
            'started_at', 'ended_at', 'due_at', 'created_at', 'updated_at',
            'amount_paid', 'overdue_amount',
            'formatted_amount_paid', 'formatted_overdue_amount',
            'current_overdue_amount', 'estimated_total_cost', 'minutes_overdue',
            'formatted_current_overdue', 'formatted_estimated_total',
            'station_name', 'station_location',
            'return_station_name', 'return_station_location',
            'package_name', 'power_bank_serial',
            'duration_used', 'time_remaining', 'is_overdue',
            'is_returned_on_time', 'timely_return_bonus_awarded',
        ]
        read_only_fields = [
            'id', 'rental_code', 'status', 'payment_status',
            'started_at', 'ended_at', 'amount_paid', 'overdue_amount',
            'is_returned_on_time', 'timely_return_bonus_awarded',
            'created_at', 'updated_at'
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_amount_paid(self, obj) -> str:
        return f"NPR {obj.amount_paid:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_overdue_amount(self, obj) -> str:
        return f"NPR {obj.overdue_amount:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_current_overdue(self, obj) -> str:
        return f"NPR {obj.current_overdue_amount:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_estimated_total(self, obj) -> str:
        return f"NPR {obj.estimated_total_cost:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_duration_used(self, obj) -> str:
        if not obj.started_at:
            return "Not started"
        
        end_time = obj.ended_at or timezone.now()
        duration = end_time - obj.started_at
        total_minutes = int(duration.total_seconds() / 60)
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_time_remaining(self, obj) -> str | None:
        if obj.status not in ['ACTIVE', 'PENDING', 'PENDING_POPUP']:
            return None
        if not obj.due_at:
            return None
        
        now = timezone.now()
        if now >= obj.due_at:
            return "Overdue"
        
        remaining = obj.due_at - now
        total_minutes = int(remaining.total_seconds() / 60)
        
        if total_minutes < 60:
            return f"{total_minutes}m remaining"
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours}h {minutes}m remaining"
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_overdue(self, obj) -> bool:
        if obj.status not in ['ACTIVE', 'OVERDUE']:
            return False
        return timezone.now() > obj.due_at if obj.due_at else False

    @extend_schema_field(
        {
            'type': 'object',
            'properties': {
                'latitude': {'type': 'number', 'nullable': True},
                'longitude': {'type': 'number', 'nullable': True},
                'address': {'type': 'string', 'nullable': True},
            },
            'nullable': True,
        }
    )
    def get_station_location(self, obj):
        station = getattr(obj, 'station', None)
        if not station:
            return None
        return {
            'latitude': float(station.latitude) if station.latitude is not None else None,
            'longitude': float(station.longitude) if station.longitude is not None else None,
            'address': station.address,
        }

    @extend_schema_field(
        {
            'type': 'object',
            'properties': {
                'latitude': {'type': 'number', 'nullable': True},
                'longitude': {'type': 'number', 'nullable': True},
                'address': {'type': 'string', 'nullable': True},
            },
            'nullable': True,
        }
    )
    def get_return_station_location(self, obj):
        station = getattr(obj, 'return_station', None)
        if not station:
            return None
        return {
            'latitude': float(station.latitude) if station.latitude is not None else None,
            'longitude': float(station.longitude) if station.longitude is not None else None,
            'address': station.address,
        }


class RentalExtensionSerializer(serializers.ModelSerializer):
    """Serializer for rental extension details."""
    package_name = serializers.CharField(source='package.name', read_only=True)
    formatted_extension_cost = serializers.SerializerMethodField()
    
    class Meta:
        model = RentalExtension
        fields = [
            'id', 'extended_minutes', 'extension_cost', 'extended_at',
            'package_name', 'formatted_extension_cost'
        ]
        read_only_fields = ['id', 'extended_at']
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_extension_cost(self, obj) -> str:
        return f"NPR {obj.extension_cost:,.2f}"


class RentalIssueSerializer(serializers.ModelSerializer):
    """Serializer for rental issues."""
    rental_code = serializers.CharField(source='rental.rental_code', read_only=True)
    issue_type = serializers.ChoiceField(choices=RentalIssue.ISSUE_TYPE_CHOICES)
    status = serializers.ChoiceField(choices=RentalIssue.STATUS_CHOICES)
    
    class Meta:
        model = RentalIssue
        fields = [
            'id', 'issue_type', 'description', 'images', 'status',
            'reported_at', 'resolved_at', 'rental_code'
        ]
        read_only_fields = ['id', 'reported_at', 'resolved_at', 'rental_code']


class RentalLocationSerializer(serializers.ModelSerializer):
    """Serializer for rental location tracking."""
    
    class Meta:
        model = RentalLocation
        fields = ['id', 'latitude', 'longitude', 'accuracy', 'recorded_at']
        read_only_fields = ['id', 'recorded_at']
