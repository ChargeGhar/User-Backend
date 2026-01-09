"""
MIGRATION NOTICE:
================
Model-specific serializers have been migrated to specialized apps:

- Country serializers → api/system/serializers.py
- MediaUpload serializers → api/media/serializers.py
- AppConfig/Version serializers → api/system/serializers.py

Please update your imports:
    from api.user.system.serializers import CountrySerializer, AppConfigSerializer
    from api.user.media.serializers import MediaUploadSerializer

This file now contains only common/base serializers used across all apps.
"""

from __future__ import annotations

from rest_framework import serializers


class BaseResponseSerializer(serializers.Serializer):
    """Standard response format for all API endpoints"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.JSONField()
    timestamp = serializers.DateTimeField()


class PaginatedResponseSerializer(serializers.Serializer):
    """Standard paginated response format"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.JSONField()
    pagination = serializers.DictField()
    timestamp = serializers.DateTimeField()


class AppVersionSerializer(serializers.Serializer):
    """App version response serializer - Generic format"""
    current_version = serializers.CharField()
    latest_version = serializers.CharField()
    update_required = serializers.BooleanField()
    update_url = serializers.URLField(required=False)
