from rest_framework import serializers
from api.common.utils.helpers import validate_phone_number
from api.user.auth.utils.user_identifier_helper import is_email
from api.user.auth.repositories import UserRepository

class OTPRequestSerializer(serializers.Serializer):
    """Serializer for OTP request - automatically detects login vs register"""
    identifier = serializers.CharField(help_text="Email or phone number")
    platform = serializers.ChoiceField(
        choices=['android', 'ios'],
        required=False, allow_null=True, default=None,
        help_text="Client platform ('android'/'ios'). Android gets SMS Retriever markers."
    )
    
    def validate_identifier(self, value):
        if is_email(value):
            try:
                serializers.EmailField().run_validation(value)
            except serializers.ValidationError:
                raise serializers.ValidationError("Invalid email format")
        else:
            if not validate_phone_number(value):
                raise serializers.ValidationError("Invalid phone number format")
        return value

class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    identifier = serializers.CharField(help_text="Email or phone number")
    otp = serializers.CharField(max_length=6, min_length=6)

class AuthCompleteSerializer(serializers.Serializer):
    """Serializer for authentication completion"""
    identifier = serializers.CharField(help_text="Email or phone number")
    verification_token = serializers.UUIDField(help_text="Token from OTP verification")
    username = serializers.CharField(max_length=150, required=False)
    referral_code = serializers.CharField(max_length=10, required=False, allow_blank=True)
    
    def validate_username(self, value):
        if value:
            value = value.strip()
            if len(value) < 3:
                raise serializers.ValidationError("Username must be at least 3 characters")
            
            # Use Repository for check
            if UserRepository().exists_by_username(value):
                raise serializers.ValidationError("Username already exists")
        return value

class LogoutSerializer(serializers.Serializer):
    """Serializer for user logout"""
    refresh_token = serializers.CharField(help_text="JWT refresh token to blacklist")
    
    def validate_refresh_token(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Refresh token is required")
        return value.strip()
