from rest_framework import serializers
from api.user.payments.models import PaymentMethod

class PaymentMethodListSerializer(serializers.ModelSerializer):
    """Minimal serializer for payment method listing"""
    
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'gateway', 'icon', 'is_active']

class PaymentMethodSerializer(serializers.ModelSerializer):
    """Standard serializer for payment methods"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'gateway', 'icon', 'is_active', 'min_amount', 
            'max_amount', 'supported_currencies'
        ]
