from rest_framework import serializers
from decimal import Decimal
from drf_spectacular.utils import extend_schema_field
from api.payments.models import WithdrawalRequest

class WithdrawalRequestSerializer(serializers.Serializer):
    """Serializer for creating withdrawal request"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1'))
    withdrawal_method = serializers.ChoiceField(choices=[
        ('esewa', 'eSewa'),
        ('khalti', 'Khalti'),
        ('bank', 'Bank Transfer')
    ])
    
    # For eSewa/Khalti
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    
    # For Bank Transfer
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    account_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    account_holder_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate_amount(self, value):
        if value > Decimal('100000'):
            raise serializers.ValidationError("Amount cannot exceed NPR 100,000")
        return value
    
    def validate(self, attrs):
        method = attrs.get('withdrawal_method')
        if method in ['esewa', 'khalti'] and not attrs.get('phone_number'):
            raise serializers.ValidationError({"phone_number": "Required for digital wallets"})
        if method == 'bank':
            for f in ['bank_name', 'account_number', 'account_holder_name']:
                if not attrs.get(f):
                    raise serializers.ValidationError({f: "Required for bank transfer"})
        return attrs

    def get_account_details(self):
        """Get account details dict based on withdrawal method"""
        method = self.validated_data.get('withdrawal_method')
        if method in ['esewa', 'khalti']:
            return {
                'method': method,
                'phone_number': self.validated_data.get('phone_number')
            }
        elif method == 'bank':
            return {
                'method': method,
                'bank_name': self.validated_data.get('bank_name'),
                'account_number': self.validated_data.get('account_number'),
                'account_holder_name': self.validated_data.get('account_holder_name')
            }
        return {'method': method}

class WithdrawalListSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal list view"""
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    formatted_amount = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'internal_reference', 'amount', 'status', 'status_display',
            'payment_method_name', 'requested_at', 'formatted_amount'
        ]
        read_only_fields = ['id', 'internal_reference', 'requested_at', 'status']
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_amount(self, obj) -> str:
        return f"NPR {obj.amount:,.2f}"

class WithdrawalSerializer(serializers.ModelSerializer):
    """Detailed withdrawal serializer"""
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    formatted_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'internal_reference', 'amount', 'processing_fee', 'net_amount',
            'status', 'status_display', 'account_details', 'admin_notes',
            'requested_at', 'processed_at', 'payment_method_name', 'formatted_amount'
        ]
        read_only_fields = ['id', 'internal_reference', 'requested_at', 'status']
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_amount(self, obj) -> str:
        return f"NPR {obj.amount:,.2f}"

class WithdrawalCancelSerializer(serializers.Serializer):
    """Serializer for withdrawal cancellation"""
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)

class WithdrawalStatusSerializer(serializers.Serializer):
    """Serializer for withdrawal status response"""
    withdrawal_id = serializers.UUIDField()
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    requested_at = serializers.DateTimeField()
