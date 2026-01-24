# api/partners/auth/serializers/password_serializers.py
"""Partner Password Management Serializers."""
from __future__ import annotations

from rest_framework import serializers

__all__ = [
    'ChangePasswordSerializer',
]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (authenticated)."""
    current_password = serializers.CharField(
        write_only=True,
        help_text="Current password"
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        help_text="New password (min 8 chars)"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        help_text="Confirm new password"
    )
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match"
            })
        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError({
                "new_password": "New password must be different from current password"
            })
        return data
