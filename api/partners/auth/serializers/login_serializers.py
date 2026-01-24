# api/partners/auth/serializers/login_serializers.py
"""Partner Login Serializers."""
from __future__ import annotations

from rest_framework import serializers

__all__ = ['PartnerLoginSerializer']


class PartnerLoginSerializer(serializers.Serializer):
    """Serializer for partner login."""
    email = serializers.EmailField(
        help_text="Partner's registered email address"
    )
    password = serializers.CharField(
        write_only=True,
        help_text="Partner's password"
    )
    # Note: No min_length validation here - login should accept any password
    # and let the authentication service validate credentials
