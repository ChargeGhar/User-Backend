# api/partners/auth/serializers/token_serializers.py
"""Partner Token Management Serializers."""
from __future__ import annotations

from rest_framework import serializers

__all__ = ['RefreshTokenSerializer', 'LogoutSerializer']


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for token refresh."""
    refresh_token = serializers.CharField(
        help_text="Refresh token from login"
    )


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout."""
    refresh_token = serializers.CharField(
        help_text="Refresh token to blacklist"
    )
