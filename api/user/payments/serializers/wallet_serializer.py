from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from api.user.payments.models import Wallet, WalletTransaction

class WalletSerializer(serializers.ModelSerializer):
    """Serializer for wallet"""
    formatted_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'currency', 'formatted_balance', 'is_active', 'updated_at']
        read_only_fields = ['id', 'updated_at']
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_balance(self, obj) -> str:
        return f"{obj.currency} {obj.balance:,.2f}"

class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for wallet transactions"""
    formatted_amount = serializers.SerializerMethodField()
    formatted_balance_before = serializers.SerializerMethodField()
    formatted_balance_after = serializers.SerializerMethodField()
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'balance_before', 'balance_after',
            'description', 'created_at', 'formatted_amount', 'formatted_balance_before',
            'formatted_balance_after'
        ]
        read_only_fields = ['id', 'created_at']
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_amount(self, obj) -> str:
        return f"NPR {obj.amount:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_balance_before(self, obj) -> str:
        return f"NPR {obj.balance_before:,.2f}"
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_balance_after(self, obj) -> str:
        return f"NPR {obj.balance_after:,.2f}"
