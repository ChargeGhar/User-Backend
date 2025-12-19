"""
Rental Analytics Serializers
"""
from __future__ import annotations
from rest_framework import serializers
from api.common.serializers import BaseResponseSerializer


class PowerBankRentalAnalyticsResponseSerializer(BaseResponseSerializer):
    """Response serializer for powerbank rental analytics"""
    
    data = serializers.DictField()
