"""
Rental Serializers - Clean & Production Ready
========================================
MVP-optimized serializers following ChargeGhar Common App patterns.

Organization:
1. List Serializers (minimal fields for performance)
2. Detail Serializers (full data for single item views)
3. Action Serializers (request payloads for POST/PUT operations)
4. Stats & Analytics Serializers
"""

from __future__ import annotations

from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field

from api.rentals.models import (
    Rental, 
    RentalExtension, 
    RentalIssue, 
    RentalLocation, 
    RentalPackage
)
from api.stations.models import Station


# ============================================================================
# LIST SERIALIZERS - Minimal fields for performance (MVP Pattern)
# ============================================================================

class RentalPackageListSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for rental packages list.
    Used in: GET /api/rentals/packages
    Fields: 8 (optimized for list view + payment model info)
    """
    formatted_price = serializers.SerializerMethodField()
    payment_model_display = serializers.SerializerMethodField()
    
    class Meta:
        model = RentalPackage
        fields = [
            'id', 
            'name', 
            'duration_minutes', 
            'price',
            'package_type',
            'payment_model',
            'is_active', 
            'formatted_price',
            'payment_model_display'
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_price(self, obj) -> str:
        """Format price in Nepal Rupees"""
        return f"NPR {obj.price:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_payment_model_display(self, obj) -> str:
        """Human-readable payment model description"""
        if obj.payment_model == 'PREPAID':
            return "Pay Before Use"
        else:
            return "Pay After Use"


class RentalListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for rental history list.
    Used in: GET /api/rentals/history
    Fields: 10 (balanced for usability & performance)
    """
    station_name = serializers.CharField(source='station.station_name', read_only=True)
    package_name = serializers.CharField(source='package.name', read_only=True)
    status_display = serializers.SerializerMethodField()
    formatted_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Rental
        fields = [
            'id', 
            'rental_code', 
            'status', 
            'status_display',
            'payment_status', 
            'started_at', 
            'ended_at',
            'station_name', 
            'package_name', 
            'formatted_amount'
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_status_display(self, obj) -> str:
        """Get human-readable status"""
        return obj.get_status_display()
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_amount(self, obj) -> str:
        """Format amount in Nepal Rupees"""
        return f"NPR {obj.amount_paid:,.2f}"


# ============================================================================
# DETAIL SERIALIZERS - Full data for single item views
# ============================================================================

class RentalDetailSerializer(serializers.ModelSerializer):
    """
    Complete serializer for rental details.
    Used in: Active rental, Start rental, Cancel rental responses
    Fields: 13+ base + 6 computed (comprehensive single rental view)
    """
    # Related fields
    station_name = serializers.CharField(source='station.station_name', read_only=True)
    return_station_name = serializers.CharField(source='return_station.station_name', read_only=True)
    package_name = serializers.CharField(source='package.name', read_only=True)
    power_bank_serial = serializers.CharField(source='power_bank.serial_number', read_only=True)
    
    # Computed fields
    formatted_amount_paid = serializers.SerializerMethodField()
    formatted_overdue_amount = serializers.SerializerMethodField()
    duration_used = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    # REALTIME fields (calculate on-demand)
    current_overdue_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Current overdue amount (realtime calculation, updates with each request)"
    )
    estimated_total_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Estimated total cost including current overdue amount"
    )
    minutes_overdue = serializers.IntegerField(
        read_only=True,
        help_text="Current minutes overdue (realtime)"
    )
    formatted_current_overdue = serializers.SerializerMethodField()
    formatted_estimated_total = serializers.SerializerMethodField()
    
    class Meta:
        model = Rental
        fields = [
            # Core fields
            'id', 
            'rental_code', 
            'status', 
            'payment_status', 
            
            # Timestamps
            'started_at',
            'ended_at', 
            'due_at', 
            'created_at', 
            'updated_at',
            
            # Financial (stored at return)
            'amount_paid', 
            'overdue_amount',
            'formatted_amount_paid',
            'formatted_overdue_amount',
            
            # Financial (realtime - calculated on demand)
            'current_overdue_amount',
            'estimated_total_cost',
            'minutes_overdue',
            'formatted_current_overdue',
            'formatted_estimated_total',
            
            # Related data
            'station_name', 
            'return_station_name',
            'package_name', 
            'power_bank_serial',
            
            # Computed
            'duration_used', 
            'time_remaining',
            'is_overdue',
            'is_returned_on_time', 
            'timely_return_bonus_awarded',
        ]
        read_only_fields = [
            'id', 
            'rental_code', 
            'status', 
            'payment_status', 
            'started_at',
            'ended_at', 
            'amount_paid', 
            'overdue_amount', 
            'is_returned_on_time',
            'timely_return_bonus_awarded', 
            'created_at', 
            'updated_at'
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_amount_paid(self, obj) -> str:
        """Format paid amount in Nepal Rupees"""
        return f"NPR {obj.amount_paid:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_overdue_amount(self, obj) -> str:
        """Format overdue amount in Nepal Rupees (final amount at return)"""
        return f"NPR {obj.overdue_amount:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_current_overdue(self, obj) -> str:
        """Format current overdue amount in Nepal Rupees (realtime)"""
        return f"NPR {obj.current_overdue_amount:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_estimated_total(self, obj) -> str:
        """Format estimated total cost in Nepal Rupees (realtime)"""
        return f"NPR {obj.estimated_total_cost:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_duration_used(self, obj) -> str:
        """Calculate duration used in human-readable format"""
        if not obj.started_at:
            return "Not started"
        
        end_time = obj.ended_at or timezone.now()
        duration = end_time - obj.started_at
        total_minutes = int(duration.total_seconds() / 60)
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_time_remaining(self, obj) -> str | None:
        """Calculate time remaining until due"""
        if obj.status not in ['ACTIVE', 'PENDING']:
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
        """Check if rental is currently overdue"""
        if obj.status not in ['ACTIVE', 'OVERDUE']:
            return False
        return timezone.now() > obj.due_at if obj.due_at else False


class RentalExtensionSerializer(serializers.ModelSerializer):
    """
    Serializer for rental extension details.
    Used in: Extension response
    """
    package_name = serializers.CharField(source='package.name', read_only=True)
    formatted_extension_cost = serializers.SerializerMethodField()
    
    class Meta:
        model = RentalExtension
        fields = [
            'id', 
            'extended_minutes', 
            'extension_cost', 
            'extended_at',
            'package_name', 
            'formatted_extension_cost'
        ]
        read_only_fields = ['id', 'extended_at']
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_extension_cost(self, obj) -> str:
        """Format extension cost in Nepal Rupees"""
        return f"NPR {obj.extension_cost:,.2f}"


class RentalIssueSerializer(serializers.ModelSerializer):
    """
    Serializer for rental issues.
    Used in: Issue list response
    """
    rental_code = serializers.CharField(source='rental.rental_code', read_only=True)
    issue_type = serializers.ChoiceField(
        choices=RentalIssue.ISSUE_TYPE_CHOICES,
        help_text="Type of rental issue"
    )
    status = serializers.ChoiceField(
        choices=RentalIssue.STATUS_CHOICES,
        help_text="Issue status"
    )
    
    class Meta:
        model = RentalIssue
        fields = [
            'id', 
            'issue_type', 
            'description', 
            'images', 
            'status',
            'reported_at', 
            'resolved_at', 
            'rental_code'
        ]
        read_only_fields = ['id', 'reported_at', 'resolved_at', 'rental_code']


class RentalLocationSerializer(serializers.ModelSerializer):
    """
    Serializer for rental location tracking.
    Used in: Location update response
    """
    
    class Meta:
        model = RentalLocation
        fields = [
            'id', 
            'latitude', 
            'longitude', 
            'accuracy', 
            'recorded_at'
        ]
        read_only_fields = ['id', 'recorded_at']


# ============================================================================
# ACTION SERIALIZERS - Request payloads for POST/PUT operations
# ============================================================================

class RentalStartSerializer(serializers.Serializer):
    """
    Request serializer for starting a rental.
    Used in: POST /api/rentals/start
    
    Note: Payment model (PREPAID/POSTPAID) is determined by the selected package,
    not by user choice. Users select packages, backend handles payment flow.
    """
    station_sn = serializers.CharField(
        max_length=255,
        help_text="Station serial number where powerbank is picked up"
    )
    package_id = serializers.UUIDField(
        help_text="Selected rental package ID (payment model determined by package)"
    )
    
    def validate_station_sn(self, value):
        """Validate station exists and is operational"""
        try:
            station = Station.objects.get(serial_number=value)
            if station.status != 'ONLINE':
                raise serializers.ValidationError("Station is not online")
            if station.is_maintenance:
                raise serializers.ValidationError("Station is under maintenance")
            return value
        except Station.DoesNotExist:
            raise serializers.ValidationError("Station not found")
    
    def validate_package_id(self, value):
        """Validate package exists and is active"""
        try:
            package = RentalPackage.objects.get(id=value, is_active=True)
            return value
        except RentalPackage.DoesNotExist:
            raise serializers.ValidationError("Package not found or inactive")
    
    def validate(self, attrs):
        """Cross-validation to ensure package and station compatibility"""
        # Get package to validate payment model compatibility
        try:
            package = RentalPackage.objects.get(id=attrs['package_id'], is_active=True)
            
            # Store package payment model for service layer access
            attrs['_package_payment_model'] = package.payment_model
            
        except RentalPackage.DoesNotExist:
            raise serializers.ValidationError({"package_id": "Package not found or inactive"})
        
        return attrs


class RentalCancelSerializer(serializers.Serializer):
    """
    Request serializer for rental cancellation.
    Used in: POST /api/rentals/{id}/cancel
    """
    reason = serializers.CharField(
        max_length=255, 
        required=False, 
        allow_blank=True,
        help_text="Optional cancellation reason"
    )
    
    def validate_reason(self, value):
        """Validate reason has minimum length if provided"""
        if value and len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Reason must be at least 5 characters if provided"
            )
        return value.strip() if value else ""


class RentalExtensionCreateSerializer(serializers.Serializer):
    """
    Request serializer for extending a rental.
    Used in: POST /api/rentals/{id}/extend
    """
    package_id = serializers.UUIDField(
        help_text="Extension package ID"
    )
    
    def validate_package_id(self, value):
        """Validate extension package exists and is active"""
        try:
            RentalPackage.objects.get(id=value, is_active=True)
            return value
        except RentalPackage.DoesNotExist:
            raise serializers.ValidationError("Package not found or inactive")


class RentalPayDueSerializer(serializers.Serializer):
    """
    Request serializer for paying rental dues.
    Used in: POST /api/rentals/pay-due
    Note: Same structure as calculate-options for post_payment scenario
    """
    scenario = serializers.ChoiceField(
        choices=['pre_payment', 'post_payment'], 
        required=True,
        help_text="Payment scenario (pre_payment for package cost, post_payment for settling dues)"
    )
    package_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Package ID (required for pre_payment scenario, optional for post_payment)"
    )
    rental_id = serializers.UUIDField(
        help_text="Rental ID with outstanding dues"
    )

    def validate_scenario(self, value):
        """Ensure valid scenario is used"""
        if value not in ['pre_payment', 'post_payment']:
            raise serializers.ValidationError(
                "Invalid scenario. Supported scenarios: pre_payment, post_payment"
            )
        return value


class RentalIssueCreateSerializer(serializers.ModelSerializer):
    """
    Request serializer for reporting rental issues.
    Used in: POST /api/rentals/{id}/issue
    """
    issue_type = serializers.ChoiceField(
        choices=RentalIssue.ISSUE_TYPE_CHOICES,
        help_text="Type of rental issue to report"
    )
    
    class Meta:
        model = RentalIssue
        fields = ['issue_type', 'description', 'images']
    
    def validate_description(self, value):
        """Validate description has minimum length"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Description must be at least 10 characters"
            )
        return value.strip()


class RentalLocationUpdateSerializer(serializers.Serializer):
    """
    Request serializer for updating rental location.
    Used in: POST /api/rentals/{id}/location
    """
    latitude = serializers.FloatField(
        help_text="GPS latitude (-90 to 90)"
    )
    longitude = serializers.FloatField(
        help_text="GPS longitude (-180 to 180)"
    )
    accuracy = serializers.FloatField(
        default=10.0,
        help_text="GPS accuracy in meters"
    )
    
    def validate_latitude(self, value):
        """Validate latitude is within valid range"""
        if not -90 <= value <= 90:
            raise serializers.ValidationError(
                "Latitude must be between -90 and 90"
            )
        return value
    
    def validate_longitude(self, value):
        """Validate longitude is within valid range"""
        if not -180 <= value <= 180:
            raise serializers.ValidationError(
                "Longitude must be between -180 and 180"
            )
        return value


# ============================================================================
# FILTER & QUERY SERIALIZERS
# ============================================================================

class RentalHistoryFilterSerializer(serializers.Serializer):
    """
    Query parameter serializer for rental history filtering.
    Used in: GET /api/rentals/history (query params)
    """
    status = serializers.ChoiceField(
        choices=Rental.RENTAL_STATUS_CHOICES,
        required=False,
        help_text="Filter by rental status"
    )
    payment_status = serializers.ChoiceField(
        choices=Rental.PAYMENT_STATUS_CHOICES,
        required=False,
        help_text="Filter by payment status"
    )
    start_date = serializers.DateTimeField(
        required=False,
        help_text="Filter rentals started after this date"
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text="Filter rentals started before this date"
    )
    station_id = serializers.UUIDField(
        required=False,
        help_text="Filter by station ID"
    )
    page = serializers.IntegerField(
        default=1, 
        min_value=1,
        help_text="Page number"
    )
    page_size = serializers.IntegerField(
        default=20, 
        min_value=1, 
        max_value=100,
        help_text="Items per page (max 100)"
    )
    
    def validate(self, attrs):
        """Cross-field validation for date range"""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "start_date cannot be after end_date"
            )
        
        return attrs


# ============================================================================
# STATS & ANALYTICS SERIALIZERS
# ============================================================================

class RentalStatsSerializer(serializers.Serializer):
    """
    Serializer for user rental statistics.
    Used in: GET /api/rentals/stats
    """
    # Rental counts
    total_rentals = serializers.IntegerField(
        help_text="Total number of rentals"
    )
    completed_rentals = serializers.IntegerField(
        help_text="Number of completed rentals"
    )
    active_rentals = serializers.IntegerField(
        help_text="Number of currently active rentals"
    )
    cancelled_rentals = serializers.IntegerField(
        help_text="Number of cancelled rentals"
    )
    
    # Financial stats
    total_spent = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Total amount spent in NPR"
    )
    
    # Duration stats
    total_time_used = serializers.IntegerField(
        help_text="Total rental time in minutes"
    )
    average_rental_duration = serializers.FloatField(
        help_text="Average rental duration in minutes"
    )
    
    # Return behavior stats
    timely_returns = serializers.IntegerField(
        help_text="Number of on-time returns"
    )
    late_returns = serializers.IntegerField(
        help_text="Number of late returns"
    )
    timely_return_rate = serializers.FloatField(
        help_text="Percentage of on-time returns (0-100)"
    )
    
    # User preferences
    favorite_station = serializers.CharField(
        allow_null=True,
        help_text="Most frequently used station"
    )
    favorite_package = serializers.CharField(
        allow_null=True,
        help_text="Most frequently selected package"
    )
    
    # Activity timeline
    last_rental_date = serializers.DateTimeField(
        allow_null=True,
        help_text="Date of last rental"
    )
    first_rental_date = serializers.DateTimeField(
        allow_null=True,
        help_text="Date of first rental"
    )
