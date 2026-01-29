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
    
    # Discount fields
    has_discount = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    
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
            'payment_model_display',
            'has_discount',
            'discount_percent',
            'original_price',
            'discounted_price',
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_price(self, obj) -> str:
        return f"NPR {obj.price:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_payment_model_display(self, obj) -> str:
        if obj.payment_model == 'PREPAID':
            return "Pay Before Use"
        return "Pay After Use"
    
    @extend_schema_field(serializers.BooleanField)
    def get_has_discount(self, obj) -> bool:
        """Check if package has discount for current station"""
        discounts = self.context.get('discounts', {})
        return str(obj.id) in discounts
    
    @extend_schema_field(serializers.DecimalField(max_digits=5, decimal_places=2))
    def get_discount_percent(self, obj):
        """Get discount percentage if available"""
        discounts = self.context.get('discounts', {})
        discount = discounts.get(str(obj.id))
        return float(discount.discount_percent) if discount else None
    
    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_original_price(self, obj):
        """Get original price if discount exists"""
        if self.get_has_discount(obj):
            return float(obj.price)
        return None
    
    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_discounted_price(self, obj):
        """Get discounted price if discount exists"""
        discounts = self.context.get('discounts', {})
        discount = discounts.get(str(obj.id))
        
        if discount:
            from api.user.promotions.services import DiscountService
            _, final_price = DiscountService.calculate_discounted_price(
                obj.price, discount.discount_percent
            )
            return float(final_price)
        return None


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
