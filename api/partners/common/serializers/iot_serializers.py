"""
Partner IoT Serializers (Common for both Franchise and Vendor)
"""

from rest_framework import serializers


class IoTEjectSerializer(serializers.Serializer):
    """Eject powerbank request"""
    
    slot_number = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True)


class IoTHistorySerializer(serializers.Serializer):
    """IoT action history item"""
    
    id = serializers.UUIDField()
    action_type = serializers.CharField()
    performed_from = serializers.CharField()
    powerbank_sn = serializers.CharField(allow_null=True)
    slot_number = serializers.IntegerField(allow_null=True)
    is_free_ejection = serializers.BooleanField()
    is_successful = serializers.BooleanField()
    error_message = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class IoTHistoryListResponseSerializer(serializers.Serializer):
    """Paginated IoT history response"""
    
    count = serializers.IntegerField()
    next = serializers.BooleanField()
    previous = serializers.BooleanField()
    results = IoTHistorySerializer(many=True)


class IoTEjectResponseSerializer(serializers.Serializer):
    """Eject powerbank response"""
    
    iot_history = IoTHistorySerializer()
    free_ejections_remaining = serializers.IntegerField(allow_null=True)
