from __future__ import annotations

from rest_framework import serializers
from api.user.content.models import ContentPage


class ContentPageSerializer(serializers.ModelSerializer):
    """Serializer for content pages"""
    
    class Meta:
        model = ContentPage
        fields = ['id', 'page_type', 'title', 'content', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_content(self, value):
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Content must be at least 50 characters")
        return value.strip()


class ContentPageListSerializer(serializers.ModelSerializer):
    """MVP serializer for content page lists - minimal fields"""
    
    class Meta:
        model = ContentPage
        fields = ['page_type', 'title', 'updated_at']
        read_only_fields = fields


class ContentPagePublicSerializer(serializers.ModelSerializer):
    """Public serializer for content pages (no admin fields)"""
    
    class Meta:
        model = ContentPage
        fields = ['page_type', 'title', 'content', 'updated_at']
