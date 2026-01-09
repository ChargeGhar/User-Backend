from rest_framework import serializers
from api.user.payments.models import Refund

class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refund details"""
    transaction_id = serializers.CharField(source='transaction.transaction_id', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    formatted_amount = serializers.CharField(source='get_formatted_amount', read_only=True)
    status = serializers.ChoiceField(
        choices=Refund.STATUS_CHOICES,
        help_text="Refund status"
    )
    
    class Meta:
        model = Refund
        fields = [
            'id', 'amount', 'reason', 'status', 'gateway_reference',
            'admin_notes', 'requested_at', 'processed_at',
            'transaction_id', 'user_name', 'formatted_amount'
        ]
        read_only_fields = ['id', 'requested_at', 'processed_at', 'status']

class RefundRequestSerializer(serializers.Serializer):
    """Serializer for refund requests"""
    transaction_id = serializers.CharField(max_length=255)
    reason = serializers.CharField(max_length=255)
    
    def validate_reason(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Reason must be at least 10 characters")
        return value.strip()
