"""
Payment Analytics Serializers
"""
from __future__ import annotations
from rest_framework import serializers
from api.common.serializers import BaseResponseSerializer


class PaymentAnalyticsResponseSerializer(BaseResponseSerializer):
    """Response serializer for payment analytics"""
    
    data = serializers.DictField()
