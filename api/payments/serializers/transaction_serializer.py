from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from api.payments.models import Transaction

class TransactionListSerializer(serializers.ModelSerializer):
    """Serializer for transaction list view"""
    formatted_amount = serializers.CharField(source='get_formatted_amount', read_only=True)
    status = serializers.ChoiceField(
        choices=Transaction.STATUS_CHOICES,
        help_text="Transaction status"
    )
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_id', 'transaction_type', 'amount', 
            'status', 'created_at', 'formatted_amount'
        ]
        read_only_fields = ['id', 'transaction_id', 'created_at', 'status']

class TransactionSerializer(serializers.ModelSerializer):
    """Detailed transaction serializer"""
    formatted_amount = serializers.CharField(source='get_formatted_amount', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True, allow_null=True)
    status = serializers.ChoiceField(
        choices=Transaction.STATUS_CHOICES,
        help_text="Transaction status"
    )
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_id', 'transaction_type', 'amount', 'currency',
            'status', 'payment_method_type', 'gateway_reference', 'created_at',
            'formatted_amount', 'payment_method_name', 'description'
        ]
        read_only_fields = ['id', 'transaction_id', 'created_at', 'status']

class TransactionDetailSerializer(TransactionSerializer):
    """Detailed serializer for single transaction view"""
    rental_code = serializers.SerializerMethodField()
    
    class Meta(TransactionSerializer.Meta):
        fields = TransactionSerializer.Meta.fields + ['rental_code']
    
    @extend_schema_field(serializers.CharField)
    def get_rental_code(self, obj) -> str:
        return obj.related_rental.rental_code if obj.related_rental else "N/A"

class UserTransactionHistorySerializer(serializers.Serializer):
    """Serializer for user transaction history filters"""
    transaction_type = serializers.ChoiceField(
        choices=Transaction.TRANSACTION_TYPE_CHOICES,
        required=False
    )
    status = serializers.ChoiceField(
        choices=Transaction.STATUS_CHOICES,
        required=False
    )
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    
    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date cannot be after end_date")
        
        return attrs
