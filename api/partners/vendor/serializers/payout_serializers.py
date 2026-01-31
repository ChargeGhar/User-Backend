"""
Vendor Payout Serializers
"""

from rest_framework import serializers


class VendorPayoutProcessorSerializer(serializers.Serializer):
    """Processed by user info"""
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()


class VendorPayoutSerializer(serializers.Serializer):
    """Single payout"""
    id = serializers.UUIDField()
    reference_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    payout_type = serializers.CharField()
    bank_name = serializers.CharField(allow_null=True)
    account_number = serializers.CharField(allow_null=True)
    account_holder_name = serializers.CharField(allow_null=True)
    requested_at = serializers.DateTimeField()
    processed_at = serializers.DateTimeField(allow_null=True)
    processed_by = VendorPayoutProcessorSerializer(allow_null=True)
    rejection_reason = serializers.CharField(allow_null=True)
    admin_notes = serializers.CharField(allow_null=True)


class VendorPayoutSummarySerializer(serializers.Serializer):
    """Payout summary"""
    pending_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2)


class VendorPayoutListSerializer(serializers.Serializer):
    """Paginated payout list"""
    results = VendorPayoutSerializer(many=True)
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    summary = VendorPayoutSummarySerializer()


class VendorPayoutRequestSerializer(serializers.Serializer):
    """Payout request input"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    bank_name = serializers.CharField()
    account_number = serializers.CharField()
    account_holder_name = serializers.CharField()


class VendorPayoutRequestResponseSerializer(serializers.Serializer):
    """Payout request response"""
    id = serializers.UUIDField()
    reference_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    payout_type = serializers.CharField()
    bank_name = serializers.CharField()
    account_number = serializers.CharField()
    account_holder_name = serializers.CharField()
    requested_at = serializers.DateTimeField()
    processor = serializers.CharField()
