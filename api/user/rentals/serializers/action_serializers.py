"""
Rental Action Serializers
=========================

Request payload serializers for POST/PUT operations.
"""
from rest_framework import serializers

from api.user.rentals.models import RentalPackage, RentalIssue
from api.user.stations.models import Station

PAYMENT_MODE_CHOICES = [
    ('wallet', 'Wallet'),
    ('points', 'Points'),
    ('wallet_points', 'Wallet + Points'),
    ('direct', 'Direct Gateway Payment'),
]


class RentalStartSerializer(serializers.Serializer):
    """
    Request serializer for starting a rental.
    Used in: POST /api/rentals/start
    """
    station_sn = serializers.CharField(
        max_length=255,
        help_text="Station serial number where powerbank is picked up"
    )
    package_id = serializers.UUIDField(
        help_text="Selected rental package ID"
    )
    powerbank_sn = serializers.CharField(
        max_length=50,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Optional: Specific powerbank SN to rent"
    )
    payment_method_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional: Payment method ID (required if payment is needed)/When selected payment_mode is 'direct' payment method ID must be provided"
    )
    payment_mode = serializers.ChoiceField(
        choices=PAYMENT_MODE_CHOICES,
        required=False,
        default='wallet_points',
        help_text="Payment mode: wallet, points, wallet_points, or direct"
    )
    wallet_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
        help_text="Optional preferred wallet amount for wallet_points mode/When selected payment_mode is 'wallet_points', both wallet_amount and points_to_use must be provided"
    )
    points_to_use = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
        help_text="Optional preferred points to use for wallet_points mode/When selected payment_mode is 'wallet_points', both wallet_amount and points_to_use must be provided"
    )
    
    def validate_station_sn(self, value):
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
        try:
            RentalPackage.objects.get(id=value, is_active=True)
            return value
        except RentalPackage.DoesNotExist:
            raise serializers.ValidationError("Package not found or inactive")
    
    def validate(self, attrs):
        try:
            package = RentalPackage.objects.get(id=attrs['package_id'], is_active=True)
            attrs['_package_payment_model'] = package.payment_model
        except RentalPackage.DoesNotExist:
            raise serializers.ValidationError({"package_id": "Package not found or inactive"})

        payment_mode = attrs.get('payment_mode', 'wallet_points')
        wallet_amount = attrs.get('wallet_amount')
        points_to_use = attrs.get('points_to_use')

        if (wallet_amount is None) ^ (points_to_use is None):
            raise serializers.ValidationError(
                {"wallet_points_split": "Provide both wallet_amount and points_to_use together"}
            )

        if payment_mode != 'wallet_points' and (wallet_amount is not None or points_to_use is not None):
            raise serializers.ValidationError(
                {"wallet_points_split": "wallet_amount and points_to_use are only valid for wallet_points mode"}
            )

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
    package_id = serializers.UUIDField(help_text="Extension package ID")
    
    def validate_package_id(self, value):
        try:
            RentalPackage.objects.get(id=value, is_active=True)
            return value
        except RentalPackage.DoesNotExist:
            raise serializers.ValidationError("Package not found or inactive")


class RentalPayDueSerializer(serializers.Serializer):
    """
    Request serializer for paying rental dues.
    Used in: POST /api/rentals/{id}/pay-due
    """
    payment_method_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional payment method ID (required if gateway top-up intent is needed)/When selected payment_mode is 'direct', payment_method_id must be provided"
    )
    payment_mode = serializers.ChoiceField(
        choices=PAYMENT_MODE_CHOICES,
        required=False,
        default='wallet_points',
        help_text="Payment mode: wallet, points, wallet_points, or direct"
    )
    wallet_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
        help_text="Optional preferred wallet amount for wallet_points mode/When selected payment_mode is 'wallet_points', both wallet_amount and points_to_use must be provided"
    )
    points_to_use = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
        help_text="Optional preferred points to use for wallet_points mode/When selected payment_mode is 'wallet_points', both wallet_amount and points_to_use must be provided"
    )

    def validate(self, attrs):
        payment_mode = attrs.get('payment_mode', 'wallet_points')
        wallet_amount = attrs.get('wallet_amount')
        points_to_use = attrs.get('points_to_use')

        if (wallet_amount is None) ^ (points_to_use is None):
            raise serializers.ValidationError(
                {"wallet_points_split": "Provide both wallet_amount and points_to_use together"}
            )

        if payment_mode != 'wallet_points' and (wallet_amount is not None or points_to_use is not None):
            raise serializers.ValidationError(
                {"wallet_points_split": "wallet_amount and points_to_use are only valid for wallet_points mode"}
            )

        return attrs


class RentalIssueCreateSerializer(serializers.ModelSerializer):
    """
    Request serializer for reporting rental issues.
    Used in: POST /api/rentals/{id}/issue
    """
    issue_type = serializers.ChoiceField(
        choices=RentalIssue.ISSUE_TYPE_CHOICES,
        help_text="Type of rental issue"
    )
    
    class Meta:
        model = RentalIssue
        fields = ['issue_type', 'description', 'images']
    
    def validate_description(self, value):
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
    latitude = serializers.FloatField(help_text="GPS latitude (-90 to 90)")
    longitude = serializers.FloatField(help_text="GPS longitude (-180 to 180)")
    accuracy = serializers.FloatField(default=10.0, help_text="GPS accuracy in meters")
    
    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value


class RentalSwapSerializer(serializers.Serializer):
    """
    Request serializer for powerbank swap.
    Used in: POST /api/rentals/{id}/swap
    """
    reason = serializers.ChoiceField(
        choices=['LOW_BATTERY', 'DEFECTIVE', 'WRONG_CABLE', 'OTHER'],
        default='OTHER',
        required=False,
        help_text="Reason for swap request"
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional description of the issue"
    )
    powerbank_sn = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text="Optional: Specific powerbank serial number to swap to"
    )
    
    def validate_description(self, value):
        if value:
            return value.strip()
        return ""
    
    def validate_powerbank_sn(self, value):
        if value:
            return value.strip()
        return None
