"""
Rental Filter Serializers
=========================

Query parameter serializers for filtering and pagination.
"""
from rest_framework import serializers

from api.user.rentals.models import Rental


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
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "start_date cannot be after end_date"
            )
        return attrs
