from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from api.payments.models import PaymentIntent
from api.payments.repositories import PaymentIntentRepository

class PaymentIntentListSerializer(serializers.ModelSerializer):
    """Serializer for payment intent list view"""
    formatted_amount = serializers.CharField(source='get_formatted_amount', read_only=True)
    status = serializers.ChoiceField(
        choices=PaymentIntent.STATUS_CHOICES,
        help_text="Payment intent status"
    )
    
    class Meta:
        model = PaymentIntent
        fields = [
            'id', 'intent_id', 'status', 'amount', 'formatted_amount', 'created_at'
        ]
        read_only_fields = ['id', 'intent_id', 'created_at', 'status']

class PaymentIntentSerializer(serializers.ModelSerializer):
    """Detailed payment intent serializer"""
    formatted_amount = serializers.CharField(source='get_formatted_amount', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True, allow_null=True)
    status = serializers.ChoiceField(
        choices=PaymentIntent.STATUS_CHOICES,
        help_text="Payment intent status"
    )
    
    class Meta:
        model = PaymentIntent
        fields = [
            'id', 'intent_id', 'intent_type', 'amount', 'currency', 'status',
            'payment_method_type', 'gateway_reference', 'callback_url',
            'created_at', 'updated_at', 'expires_at',
            'formatted_amount', 'payment_method_name', 'metadata'
        ]
        read_only_fields = ['id', 'intent_id', 'created_at', 'updated_at', 'status']

class TopupIntentCreateSerializer(serializers.Serializer):
    """Serializer for creating top-up intent"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('10'))
    payment_method_id = serializers.UUIDField()
    
    def validate_amount(self, value):
        if value > Decimal('50000'):  # Max NPR 50,000
            raise serializers.ValidationError("Amount cannot exceed NPR 50,000")
        return value

class PaymentStatusSerializer(serializers.Serializer):
    """Serializer for payment status response"""
    intent_id = serializers.CharField()
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    gateway_reference = serializers.CharField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    failure_reason = serializers.CharField(allow_null=True)

class VerifyTopupSerializer(serializers.Serializer):
    """Serializer for verifying top-up payment with callback data"""
    intent_id = serializers.CharField()
    callback_data = serializers.JSONField(required=False)
    
    # Support legacy fields for backward compatibility
    gateway_reference = serializers.CharField(required=False, allow_blank=True)
    data = serializers.CharField(required=False, allow_blank=True)  # eSewa base64 data
    pidx = serializers.CharField(required=False, allow_blank=True)  # Khalti pidx
    status = serializers.CharField(required=False, allow_blank=True)  # Khalti status
    txnId = serializers.CharField(required=False, allow_blank=True)  # Khalti txnId
    
    def validate_intent_id(self, value):
        repository = PaymentIntentRepository()
        intent = repository.get_by_intent_id(value)
        if not intent:
            raise serializers.ValidationError("Invalid payment intent")
            
        if intent.status not in ['PENDING', 'COMPLETED']:
            raise serializers.ValidationError(f"Payment intent status is {intent.status}, cannot verify")
        
        if intent.status == 'PENDING' and timezone.now() > intent.expires_at:
            raise serializers.ValidationError("Payment intent has expired")
            
        return value
    
    def validate(self, attrs):
        if not attrs.get('callback_data'):
            callback_data = {}
            if attrs.get('data'): callback_data['data'] = attrs['data']
            if attrs.get('pidx'):
                callback_data['pidx'] = attrs['pidx']
                if attrs.get('status'): callback_data['status'] = attrs['status']
                if attrs.get('txnId'): callback_data['txnId'] = attrs['txnId']
            if attrs.get('gateway_reference') and not callback_data:
                callback_data['gateway_reference'] = attrs['gateway_reference']
            attrs['callback_data'] = callback_data
        return attrs
