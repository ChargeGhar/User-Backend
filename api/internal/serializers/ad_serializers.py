"""
Internal Advertisement Serializers
===================================
Serializers for device-facing ad distribution endpoints.
"""
from __future__ import annotations

from rest_framework import serializers


class AdDistributionItemSerializer(serializers.Serializer):
    """
    Single advertisement item for device response.
    Matches manufacturer API contract exactly.
    """
    id = serializers.CharField(help_text="Unique ad content ID")
    title = serializers.CharField(help_text="Ad title")
    file_type = serializers.IntegerField(help_text="0=image, 1=video")
    url_small = serializers.URLField(help_text="URL for < 20 slot stations")
    url_large = serializers.URLField(help_text="URL for >= 20 slot stations")
    url3 = serializers.CharField(help_text="Reserved", default="")
    forward = serializers.CharField(help_text="Redirect/forward URL", default="")
    play_time = serializers.IntegerField(help_text="Display duration in seconds")
    weight = serializers.IntegerField(help_text="Display priority")
    screen_brightness = serializers.IntegerField(help_text="Screen brightness 0-255")
    guuid = serializers.CharField(help_text="Content UUID")
    position = serializers.CharField(help_text="Position/screen identifier", default="ALL")
