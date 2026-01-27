"""
Rental List Serializers
=======================

Minimal serializers optimized for list views and performance.
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from api.user.rentals.models import Rental, RentalPackage


class RentalPackageListSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for rental packages list.
    Used in: GET /api/rentals/packages
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
        return f"NPR {obj.price:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_payment_model_display(self, obj) -> str:
        if obj.payment_model == 'PREPAID':
            return "Pay Before Use"
        return "Pay After Use"


class RentalListSerializer(serializers.ModelSerializer):
    """
    Deprecated (kept for backward compatibility):
    History now returns `RentalDetailSerializer` for consistent item format.
    """
    station_name = serializers.CharField(source='station.station_name', read_only=True)
    package_name = serializers.CharField(source='package.name', read_only=True)

    class Meta:
        model = Rental
        fields = [
            'id',
            'rental_code',
            'status',
            'payment_status',
            'started_at',
            'ended_at',
            'station_name',
            'package_name',
        ]
