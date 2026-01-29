"""
Admin Discount Serializers
"""
from rest_framework import serializers
from api.user.promotions.models import StationPackageDiscount


class CreateDiscountSerializer(serializers.Serializer):
    """Serializer for creating station package discount"""
    station_id = serializers.UUIDField()
    package_id = serializers.UUIDField()
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100
    )
    max_total_uses = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    max_uses_per_user = serializers.IntegerField(default=1, min_value=1)
    valid_from = serializers.DateTimeField()
    valid_until = serializers.DateTimeField()
    status = serializers.ChoiceField(
        choices=['ACTIVE', 'INACTIVE'], default='ACTIVE'
    )
    
    def validate(self, data):
        if data['valid_until'] <= data['valid_from']:
            raise serializers.ValidationError(
                "valid_until must be after valid_from"
            )
        return data


class UpdateDiscountSerializer(serializers.Serializer):
    """Serializer for updating station package discount"""
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100, required=False
    )
    max_total_uses = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    max_uses_per_user = serializers.IntegerField(required=False, min_value=1)
    valid_from = serializers.DateTimeField(required=False)
    valid_until = serializers.DateTimeField(required=False)
    status = serializers.ChoiceField(
        choices=['ACTIVE', 'INACTIVE', 'EXPIRED'], required=False
    )


class DiscountListSerializer(serializers.ModelSerializer):
    """Serializer for discount list"""
    station_name = serializers.CharField(source='station.station_name', read_only=True)
    package_name = serializers.CharField(source='package.name', read_only=True)
    usage_count = serializers.IntegerField(source='current_usage_count', read_only=True)
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = StationPackageDiscount
        fields = [
            'id', 'station_name', 'package_name', 'discount_percent',
            'max_total_uses', 'max_uses_per_user', 'usage_count',
            'valid_from', 'valid_until', 'status', 'is_valid', 'created_at'
        ]
    
    def get_is_valid(self, obj):
        return obj.is_valid()


class DiscountDetailSerializer(DiscountListSerializer):
    """Serializer for discount detail"""
    station = serializers.SerializerMethodField()
    package = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(
        source='created_by.username', read_only=True, allow_null=True
    )
    
    class Meta(DiscountListSerializer.Meta):
        fields = DiscountListSerializer.Meta.fields + [
            'station', 'package', 'created_by_username', 'updated_at'
        ]
    
    def get_station(self, obj):
        return {
            'id': str(obj.station.id),
            'name': obj.station.station_name,
            'serial_number': obj.station.serial_number
        }
    
    def get_package(self, obj):
        return {
            'id': str(obj.package.id),
            'name': obj.package.name,
            'price': float(obj.package.price),
            'duration_minutes': obj.package.duration_minutes
        }


class DiscountFiltersSerializer(serializers.Serializer):
    """Serializer for discount filters"""
    station_id = serializers.UUIDField(required=False)
    package_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=['ACTIVE', 'INACTIVE', 'EXPIRED'], required=False
    )
