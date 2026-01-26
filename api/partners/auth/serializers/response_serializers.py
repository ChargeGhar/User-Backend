# api/partners/auth/serializers/response_serializers.py
"""Partner Auth Response Serializers."""
from __future__ import annotations

from rest_framework import serializers

__all__ = [
    'PartnerProfileSerializer',
    'AuthResponseSerializer',
    'TokenRefreshResponseSerializer',
    'MessageResponseSerializer',
]


class UserProfileDataSerializer(serializers.Serializer):
    """Nested serializer for user profile data."""
    full_name = serializers.CharField(allow_null=True, read_only=True)
    date_of_birth = serializers.CharField(allow_null=True, read_only=True)
    address = serializers.CharField(allow_null=True, read_only=True)
    avatar_url = serializers.URLField(allow_null=True, read_only=True)


class PartnerProfileSerializer(serializers.Serializer):
    """Response serializer for partner profile."""
    id = serializers.UUIDField(read_only=True)
    partner_type = serializers.CharField(read_only=True)
    vendor_type = serializers.CharField(allow_null=True, read_only=True)
    code = serializers.CharField(read_only=True)
    business_name = serializers.CharField(read_only=True)
    contact_phone = serializers.CharField(read_only=True)
    contact_email = serializers.CharField(allow_null=True, read_only=True)
    status = serializers.CharField(read_only=True)
    balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    total_earnings = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    # User profile data
    profile = UserProfileDataSerializer(read_only=True)


class AuthResponseSerializer(serializers.Serializer):
    """Response serializer for login/set-password."""
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    partner = PartnerProfileSerializer(read_only=True)


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Response serializer for token refresh."""
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)


class MessageResponseSerializer(serializers.Serializer):
    """Generic message response serializer."""
    message = serializers.CharField(read_only=True)
