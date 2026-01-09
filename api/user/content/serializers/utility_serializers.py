from __future__ import annotations

from rest_framework import serializers


class ContentAnalyticsSerializer(serializers.Serializer):
    """Serializer for content analytics"""
    total_pages = serializers.IntegerField()
    total_faqs = serializers.IntegerField()
    total_banners = serializers.IntegerField()
    active_banners = serializers.IntegerField()
    
    # Popular content
    popular_pages = serializers.ListField()
    popular_faqs = serializers.ListField()
    
    # Recent activity
    recent_updates = serializers.ListField()
    
    last_updated = serializers.DateTimeField()
