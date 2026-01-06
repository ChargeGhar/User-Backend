from rest_framework import serializers
from api.users.models import UserDevice

class UserDeviceSerializer(serializers.ModelSerializer):
    """Serializer for user device registration"""
    class Meta:
        model = UserDevice
        fields = [
            'id', 'device_id', 'fcm_token', 'device_type', 'device_name',
            'app_version', 'os_version', 'is_active', 'last_used'
        ]
        read_only_fields = ['id', 'last_used']
    
    def validate_fcm_token(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Invalid FCM token")
        return value.strip()
