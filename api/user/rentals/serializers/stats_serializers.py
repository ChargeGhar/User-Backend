"""
Rental Stats Serializers
========================

Serializers for statistics and analytics responses.
"""
from rest_framework import serializers


class RentalStatsSerializer(serializers.Serializer):
    """
    Serializer for user rental statistics.
    Used in: GET /api/rentals/stats
    """
    # Rental counts
    total_rentals = serializers.IntegerField(help_text="Total number of rentals")
    completed_rentals = serializers.IntegerField(help_text="Number of completed rentals")
    active_rentals = serializers.IntegerField(help_text="Number of currently active rentals")
    cancelled_rentals = serializers.IntegerField(help_text="Number of cancelled rentals")
    
    # Financial stats
    total_spent = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total amount spent in NPR"
    )
    
    # Duration stats
    total_time_used = serializers.IntegerField(help_text="Total rental time in minutes")
    average_rental_duration = serializers.FloatField(help_text="Average rental duration in minutes")
    
    # Return behavior stats
    timely_returns = serializers.IntegerField(help_text="Number of on-time returns")
    late_returns = serializers.IntegerField(help_text="Number of late returns")
    timely_return_rate = serializers.FloatField(help_text="Percentage of on-time returns (0-100)")
    
    # User preferences
    favorite_station = serializers.CharField(allow_null=True, help_text="Most frequently used station")
    favorite_package = serializers.CharField(allow_null=True, help_text="Most frequently selected package")
    
    # Activity timeline
    last_rental_date = serializers.DateTimeField(allow_null=True, help_text="Date of last rental")
    first_rental_date = serializers.DateTimeField(allow_null=True, help_text="Date of first rental")
