from __future__ import annotations

from rest_framework import serializers
from django.utils import timezone
from api.user.content.models import Banner


class BannerSerializer(serializers.ModelSerializer):
    """Serializer for banners"""
    is_currently_active = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'description', 'image_url', 'redirect_url',
            'display_order', 'is_active', 'valid_from', 'valid_until',
            'created_at', 'updated_at', 'is_currently_active', 'days_remaining'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_is_currently_active(self, obj) -> bool:
        now = timezone.now()
        return (obj.is_active and 
                obj.valid_from <= now <= obj.valid_until)
    
    def get_days_remaining(self, obj) -> int:
        if not obj.is_active:
            return 0
        
        now = timezone.now()
        if now > obj.valid_until:
            return 0
        
        remaining = obj.valid_until - now
        return remaining.days
    
    def validate(self, attrs):
        valid_from = attrs.get('valid_from')
        valid_until = attrs.get('valid_until')
        
        if valid_from and valid_until and valid_from >= valid_until:
            raise serializers.ValidationError("valid_from must be before valid_until")
        
        return attrs


class BannerListSerializer(serializers.ModelSerializer):
    """MVP serializer for banner lists - minimal fields"""
    
    class Meta:
        model = Banner
        fields = ['id', 'title', 'image_url', 'display_order']
        read_only_fields = fields


class BannerPublicSerializer(serializers.ModelSerializer):
    """Public serializer for active banners"""
    
    class Meta:
        model = Banner
        fields = ['id', 'title', 'description', 'image_url', 'redirect_url', 'display_order']
