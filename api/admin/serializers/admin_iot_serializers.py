"""
Admin IoT Serializers
"""

from rest_framework import serializers


class AdminIoTHistorySerializer(serializers.Serializer):
    """Admin IoT history - single row auditable format"""
    id = serializers.UUIDField()
    partner_code = serializers.CharField()
    partner_name = serializers.CharField()
    partner_type = serializers.CharField()
    station_name = serializers.CharField()
    station_sn = serializers.CharField()
    performed_by = serializers.EmailField()
    action_type = serializers.CharField()
    performed_from = serializers.CharField()
    powerbank_sn = serializers.CharField(allow_null=True)
    slot_number = serializers.IntegerField(allow_null=True)
    is_free_ejection = serializers.BooleanField()
    is_successful = serializers.BooleanField()
    error_message = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
