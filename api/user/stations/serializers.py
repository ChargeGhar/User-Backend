from __future__ import annotations

from typing import Optional
from datetime import datetime, time

from rest_framework import serializers
from django.db.models import Count, Avg
from django.utils import timezone
from decimal import Decimal
from drf_spectacular.utils import extend_schema_field

from api.user.stations.models import (
    Station, StationSlot, StationAmenity, StationAmenityMapping,
    StationIssue, StationMedia, UserStationFavorite, PowerBank
)
from api.common.utils.helpers import calculate_distance
from api.common.serializers import BaseResponseSerializer


class StationLocationMixin:
    """Mixin for common station location and favorite calculations"""
    
    def get_distance(self, obj) -> Optional[float]:
        """Calculate distance from user location if provided"""
        request = self.context.get('request')
        if not request:
            return None
        
        user_lat = request.query_params.get('lat')
        user_lng = request.query_params.get('lng')
        
        if user_lat and user_lng:
            try:
                user_lat = float(user_lat)
                user_lng = float(user_lng)
                distance = calculate_distance(
                    user_lat, user_lng,
                    float(obj.latitude), float(obj.longitude)
                )
                return round(distance, 2)
            except (ValueError, TypeError):
                pass
        
        return None
    
    def get_is_favorite(self, obj) -> bool:
        """Check if station is user's favorite"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserStationFavorite.objects.filter(
                user=request.user, station=obj
            ).exists()
        return False
    
    def get_available_slots(self, obj) -> int:
        """Get count of available slots"""
        return obj.slots.filter(status='AVAILABLE').count()


class StationAmenitySerializer(serializers.ModelSerializer):
    """Serializer for station amenities"""
    
    class Meta:
        model = StationAmenity
        fields = ['id', 'name', 'icon', 'description', 'is_active']


class PowerBankSerializer(serializers.ModelSerializer):
    """Serializer for power bank details"""
    class Meta:
        model = PowerBank
        fields = [
            'id', 'serial_number', 'model', 'capacity_mah', 
            'status', 'battery_level'
        ]
        read_only_fields = ['id']


class StationSlotSerializer(serializers.ModelSerializer):
    """Serializer for station slots"""
    status = serializers.ChoiceField(
        choices=StationSlot.SLOT_STATUS_CHOICES,
        help_text="Slot status"
    )
    powerbank = serializers.SerializerMethodField()
    
    class Meta:
        model = StationSlot
        fields = [
            'id', 'slot_number', 'status', 'battery_level', 
            'last_updated', 'current_rental', 'powerbank'
        ]
        read_only_fields = ['id', 'last_updated']
    
    @extend_schema_field(PowerBankSerializer(allow_null=True))
    def get_powerbank(self, obj) -> Optional[dict]:
        """Get powerbank details if assigned to this slot"""
        try:
            from api.user.stations.models import PowerBank
            powerbank = PowerBank.objects.filter(current_slot=obj).first()
            if powerbank:
                return PowerBankSerializer(powerbank).data
        except Exception:
            pass
        return None


class StationMediaSerializer(serializers.ModelSerializer):
    """Serializer for station media"""
    media_url = serializers.SerializerMethodField()
    
    class Meta:
        model = StationMedia
        fields = [
            'id', 'media_type', 'title', 'description', 
            'is_primary', 'media_url'
        ]
    
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_media_url(self, obj) -> Optional[str]:
        return obj.media_upload.file_url if obj.media_upload else None


class StationAmenityMappingSerializer(serializers.ModelSerializer):
    """Serializer for station amenity mappings"""
    amenity = StationAmenitySerializer(read_only=True)
    
    class Meta:
        model = StationAmenityMapping
        fields = ['amenity', 'is_available', 'notes']


class StationListSerializer(serializers.ModelSerializer, StationLocationMixin):
    """Serializer for station list view"""
    distance = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    media = StationMediaSerializer(many=True, read_only=True)
    status = serializers.ChoiceField(
        choices=Station.STATION_STATUS_CHOICES,
        help_text="Station operational status"
    )
    
    class Meta:
        model = Station
        fields = [
            'id', 'serial_number', 'station_name', 'latitude', 'longitude', 
            'address', 'status', 'total_slots', 'available_slots',
            'distance', 'is_favorite', 'media', 'opening_time', 'closing_time'
        ]
        read_only_fields = ['id']


class StationDetailSerializer(serializers.ModelSerializer, StationLocationMixin):
    """Serializer for detailed station view"""
    slots = StationSlotSerializer(many=True, read_only=True)
    amenities = serializers.SerializerMethodField()
    media = StationMediaSerializer(many=True, read_only=True)
    distance = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    status = serializers.ChoiceField(
        choices=Station.STATION_STATUS_CHOICES,
        help_text="Station operational status"
    )
    
    class Meta:
        model = Station
        fields = [
            'id', 'station_name', 'serial_number', 'latitude', 'longitude',
            'address', 'landmark', 'description', 'total_slots', 'status', 'is_maintenance',
            'slots', 'amenities', 'media', 'distance', 'available_slots',
            'is_favorite', 'hardware_info', 'opening_time', 'closing_time'
        ]
        read_only_fields = ['id']
    
    @extend_schema_field(serializers.ListField)
    def get_amenities(self, obj):
        """Get available amenities"""
        mappings = obj.amenity_mappings.filter(is_available=True).select_related('amenity')
        return StationAmenitySerializer([m.amenity for m in mappings], many=True).data
    
    @extend_schema_field(serializers.IntegerField)
    def get_occupied_slots(self, obj) -> int:
        return obj.slots.filter(status='OCCUPIED').count()
    
    @extend_schema_field(serializers.IntegerField)
    def get_maintenance_slots(self, obj) -> int:
        return obj.slots.filter(status='MAINTENANCE').count()


class StationIssueSerializer(serializers.ModelSerializer):
    """Serializer for station issues"""
    station_name = serializers.CharField(source='station.station_name', read_only=True)
    reporter_name = serializers.CharField(source='reported_by.username', read_only=True)
    issue_type = serializers.ChoiceField(
        choices=StationIssue.ISSUE_TYPE_CHOICES,
        help_text="Type of station issue"
    )
    status = serializers.ChoiceField(
        choices=StationIssue.STATUS_CHOICES,
        help_text="Issue resolution status"
    )
    
    class Meta:
        model = StationIssue
        fields = [
            'id', 'station', 'station_name', 'issue_type', 'description', 'images',
            'priority', 'status', 'reported_at', 'resolved_at', 'reporter_name'
        ]
        read_only_fields = ['id', 'reported_at', 'resolved_at', 'station_name', 'reporter_name']
    
    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters")
        return value.strip()


class StationIssueCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating station issues"""
    issue_type = serializers.ChoiceField(
        choices=StationIssue.ISSUE_TYPE_CHOICES,
        help_text="Type of station issue to report"
    )
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        help_text="List of image URLs"
    )
    
    class Meta:
        model = StationIssue
        fields = ['issue_type', 'description', 'images']
    
    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters")
        return value.strip()
    
    def validate_images(self, value):
        if value is None:
            return []
        return value

class NearbyStationsSerializer(serializers.Serializer):
    """Serializer for nearby stations request"""
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    radius = serializers.FloatField(default=5.0, min_value=0.1, max_value=50.0)
    
    def validate_lat(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_lng(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value

class StationListResponseSerializer(serializers.Serializer):
    """Response serializer for station list"""
    count = serializers.IntegerField()
    next = serializers.BooleanField()
    previous = serializers.BooleanField()
    results = serializers.ListField(child=StationListSerializer())


class StationDetailResponseSerializer(serializers.Serializer):
    """Response serializer for station detail"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = StationDetailSerializer()


class StationFavoriteToggleDataSerializer(serializers.Serializer):
    """Data serializer for favorite toggle response"""
    is_favorite = serializers.BooleanField(help_text="Whether station is now in favorites")
    message = serializers.CharField(help_text="Status message")


class StationFavoriteResponseSerializer(serializers.Serializer):
    """Response serializer for station favorite operations"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = StationFavoriteToggleDataSerializer()


class StationIssueResponseSerializer(serializers.Serializer):
    """Response serializer for station issue creation"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = StationIssueSerializer()


class UserFavoriteStationsResponseSerializer(serializers.Serializer):
    """Response serializer for user favorite stations"""
    count = serializers.IntegerField()
    next = serializers.BooleanField()
    previous = serializers.BooleanField()
    results = serializers.ListField(child=StationListSerializer())


class UserIssueReportsQuerySerializer(serializers.Serializer):
    """Query serializer for unified issue reports endpoint."""
    issue_scope = serializers.ChoiceField(
        choices=['all', 'station', 'rental'],
        required=False,
        help_text="Scope of issue reports: all | station | rental"
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=50)

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date cannot be after end_date")

        return attrs

    def get_reported_at_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Build inclusive datetime range for reported_at from validated date inputs."""
        start_date = self.validated_data.get('start_date')
        end_date = self.validated_data.get('end_date')

        start_dt = None
        end_dt = None

        if start_date:
            start_dt = datetime.combine(start_date, time.min)
            if timezone.is_naive(start_dt):
                start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())

        if end_date:
            end_dt = datetime.combine(end_date, time.max)
            if timezone.is_naive(end_dt):
                end_dt = timezone.make_aware(end_dt, timezone.get_current_timezone())

        return start_dt, end_dt


class IssueStationMetaSerializer(serializers.Serializer):
    """Station metadata inside unified issue row."""
    id = serializers.UUIDField()
    serial_number = serializers.CharField()
    station_name = serializers.CharField()


class IssueRentalMetaSerializer(serializers.Serializer):
    """Rental metadata inside unified issue row."""
    id = serializers.UUIDField()
    rental_code = serializers.CharField()


class UserIssueReportSerializer(serializers.Serializer):
    """Unified issue row serializer for station and rental reports."""
    id = serializers.UUIDField()
    issue_scope = serializers.ChoiceField(choices=['station', 'rental'])
    issue_type = serializers.CharField()
    description = serializers.CharField()
    images = serializers.ListField(child=serializers.CharField(), default=list)
    status = serializers.CharField()
    priority = serializers.CharField(allow_null=True, required=False)
    reported_at = serializers.DateTimeField()
    resolved_at = serializers.DateTimeField(allow_null=True, required=False)
    station = IssueStationMetaSerializer(allow_null=True, required=False)
    rental = IssueRentalMetaSerializer(allow_null=True, required=False)


class UserIssueReportsResponseSerializer(serializers.Serializer):
    """Response serializer for unified user issue reports."""
    count = serializers.IntegerField()
    next = serializers.BooleanField()
    previous = serializers.BooleanField()
    results = UserIssueReportSerializer(many=True)
