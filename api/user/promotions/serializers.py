from __future__ import annotations

from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field

from api.user.promotions.models import Coupon, CouponUsage
from api.common.serializers import BaseResponseSerializer

# MVP Pattern: List vs Detail Serializers


class CouponListSerializer(serializers.ModelSerializer):
    """Minimal serializer for coupon lists - MVP optimized"""
    is_currently_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'name', 'points_value', 
            'valid_until', 'is_currently_valid'
        ]
        read_only_fields = ['id']
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_currently_valid(self, obj) -> bool:
        now = timezone.now()
        return (obj.status == Coupon.StatusChoices.ACTIVE and 
                obj.valid_from <= now <= obj.valid_until)


class CouponDetailSerializer(serializers.ModelSerializer):
    """Detailed coupon serializer with validation info"""
    is_currently_valid = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    total_uses = serializers.SerializerMethodField()
    status = serializers.ChoiceField(
        choices=Coupon.StatusChoices.choices,
        help_text="Coupon status"
    )
    
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'name', 'points_value', 'max_uses_per_user',
            'valid_from', 'valid_until', 'status', 'created_at',
            'is_currently_valid', 'days_remaining', 'total_uses'
        ]
        read_only_fields = ['id', 'created_at', 'status']
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_currently_valid(self, obj) -> bool:
        now = timezone.now()
        return (obj.status == Coupon.StatusChoices.ACTIVE and 
                obj.valid_from <= now <= obj.valid_until)
    
    @extend_schema_field(serializers.IntegerField)
    def get_days_remaining(self, obj) -> int:
        if obj.status != Coupon.StatusChoices.ACTIVE:
            return 0
        
        now = timezone.now()
        if now > obj.valid_until:
            return 0
        
        remaining = obj.valid_until - now
        return remaining.days
    
    @extend_schema_field(serializers.IntegerField)
    def get_total_uses(self, obj) -> int:
        return obj.usages.count()
    
    def validate(self, attrs):
        valid_from = attrs.get('valid_from')
        valid_until = attrs.get('valid_until')
        
        if valid_from and valid_until and valid_from >= valid_until:
            raise serializers.ValidationError("valid_from must be before valid_until")
        
        return attrs


# Backward compatibility alias
CouponSerializer = CouponDetailSerializer


class CouponPublicSerializer(CouponListSerializer):
    """Public serializer for active coupons - inherits from list serializer"""
    days_remaining = serializers.SerializerMethodField()
    
    class Meta(CouponListSerializer.Meta):
        fields = CouponListSerializer.Meta.fields + ['days_remaining', 'max_uses_per_user']
    
    @extend_schema_field(serializers.IntegerField)
    def get_days_remaining(self, obj):
        now = timezone.now()
        if now > obj.valid_until:
            return 0
        
        remaining = obj.valid_until - now
        return remaining.days





class CouponUsageListSerializer(serializers.ModelSerializer):
    """Minimal serializer for coupon usage lists - MVP optimized"""
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    
    class Meta:
        model = CouponUsage
        fields = [
            'id', 'coupon_code', 'points_awarded', 'used_at'
        ]
        read_only_fields = ['id', 'used_at']


class CouponUsageDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for coupon usage - Full data"""
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    coupon_name = serializers.CharField(source='coupon.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = CouponUsage
        fields = [
            'id', 'coupon_code', 'coupon_name', 'user_username',
            'points_awarded', 'used_at'
        ]
        read_only_fields = ['id', 'used_at']


# Backward compatibility alias
CouponUsageSerializer = CouponUsageDetailSerializer


class CouponApplySerializer(serializers.Serializer):
    """Serializer for applying coupons"""
    coupon_code = serializers.CharField(max_length=10)
    
    def validate_coupon_code(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Invalid coupon code")
        return value.strip().upper()


class CouponValidationSerializer(serializers.Serializer):
    """Serializer for coupon validation response"""
    valid = serializers.BooleanField()
    coupon_code = serializers.CharField()
    points_value = serializers.IntegerField()
    message = serializers.CharField()
    can_use = serializers.BooleanField()
    uses_remaining = serializers.IntegerField()


class UserCouponHistorySerializer(CouponUsageListSerializer):
    """Serializer for user's coupon usage history - inherits from list serializer"""
    coupon_name = serializers.CharField(source='coupon.name', read_only=True)
    
    class Meta(CouponUsageListSerializer.Meta):
        fields = CouponUsageListSerializer.Meta.fields + ['coupon_name']





class CouponFilterSerializer(serializers.Serializer):
    """Serializer for coupon filtering"""
    status = serializers.ChoiceField(
        choices=Coupon.StatusChoices.choices,
        required=False
    )
    search = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    
    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date cannot be after end_date")
        
        return attrs


# Response Serializers for Swagger Documentation

class ActiveCouponsResponseSerializer(BaseResponseSerializer):
    """Response serializer for active coupons endpoint"""
    data = CouponPublicSerializer(many=True)


class CouponApplyResponseSerializer(BaseResponseSerializer):
    """Response serializer for coupon apply endpoint"""
    class CouponApplyDataSerializer(serializers.Serializer):
        success = serializers.BooleanField()
        coupon_code = serializers.CharField()
        coupon_name = serializers.CharField()
        points_awarded = serializers.IntegerField()
        message = serializers.CharField()
    
    data = CouponApplyDataSerializer()





class MyCouponsResponseSerializer(BaseResponseSerializer):
    """Response serializer for my coupons endpoint"""
    class MyCouponsDataSerializer(serializers.Serializer):
        results = UserCouponHistorySerializer(many=True)
        pagination = serializers.DictField()
    
    data = MyCouponsDataSerializer()



