"""
Serializers for internal IoT action endpoints.
"""
from __future__ import annotations

from rest_framework import serializers


class IoTStationActionSerializer(serializers.Serializer):
    """Common payload for station-level IoT actions."""

    station_id = serializers.UUIDField()


class IoTCheckRequestSerializer(IoTStationActionSerializer):
    """Payload for check action."""

    # Backward compatible alias for old payload shape.
    include_empty = serializers.BooleanField(required=False)
    # Contract-aligned key used by partner integration.
    checkAll = serializers.BooleanField(required=False)

    def validate(self, attrs):
        include_empty = attrs.get('include_empty')
        check_all = attrs.get('checkAll')

        if include_empty is not None and check_all is not None and include_empty != check_all:
            raise serializers.ValidationError(
                {"checkAll": "checkAll conflicts with include_empty"}
            )

        if check_all is None:
            check_all = include_empty

        attrs['check_all'] = True if check_all is None else bool(check_all)
        return attrs


class IoTWifiConnectRequestSerializer(IoTStationActionSerializer):
    """Payload for WiFi connect action."""

    wifi_ssid = serializers.CharField(max_length=255)
    wifi_password = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True
    )


class IoTVolumeRequestSerializer(IoTStationActionSerializer):
    """Payload for volume action."""

    volume = serializers.IntegerField(min_value=0, max_value=100)


class IoTModeRequestSerializer(IoTStationActionSerializer):
    """Payload for mode action."""

    mode = serializers.ChoiceField(choices=['wifi', '4g'])


class IoTEjectRequestSerializer(IoTStationActionSerializer):
    """Payload for eject action."""

    powerbank_sn = serializers.CharField(max_length=255, required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        powerbank_sn = attrs.get('powerbank_sn')
        if isinstance(powerbank_sn, str):
            powerbank_sn = powerbank_sn.strip() or None
            attrs['powerbank_sn'] = powerbank_sn
        return attrs
