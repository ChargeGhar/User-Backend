from rest_framework import serializers
from api.user.auth.models import UserDevice


class UserDeviceSerializer(serializers.Serializer):
    """Serializer for user device registration/update
    
    Uses Serializer instead of ModelSerializer to avoid unique constraint
    validation issues when updating existing devices with the same device_id.
    The repository handles create_or_update logic.
    """
    device_id = serializers.CharField(max_length=255, required=True)
    fcm_token = serializers.CharField(required=True)
    device_type = serializers.ChoiceField(
        choices=UserDevice.DEVICE_TYPE_CHOICES,
        required=True
    )
    device_name = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    app_version = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    os_version = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    
    def validate_fcm_token(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Invalid FCM token")
        return value.strip()


class UserDeviceResponseSerializer(serializers.ModelSerializer):
    """Serializer for device response data (read-only)"""
    class Meta:
        model = UserDevice
        fields = [
            'id', 'device_id', 'fcm_token', 'device_type', 'device_name',
            'app_version', 'os_version', 'is_active', 'last_used', 'biometric_enabled'
        ]
        read_only_fields = fields
