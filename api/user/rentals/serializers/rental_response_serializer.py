"""
Rental Response Serializers
===========================

Response serializers for rental start endpoint.
Defines nested response structure as per specification.
"""
from rest_framework import serializers


class PackageResponseSerializer(serializers.Serializer):
    """Package details in response"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_model = serializers.CharField()


class PricingResponseSerializer(serializers.Serializer):
    """Pricing breakdown in response"""
    original_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    actual_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)


class PaymentBreakdownSerializer(serializers.Serializer):
    """Payment breakdown details"""
    wallet_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    points_used = serializers.IntegerField()
    points_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class PaymentResponseSerializer(serializers.Serializer):
    """Payment details in response"""
    payment_model = serializers.CharField()
    payment_mode = serializers.CharField(allow_null=True)
    payment_status = serializers.CharField()
    breakdown = PaymentBreakdownSerializer(allow_null=True, required=False)
    pending_transaction_id = serializers.UUIDField(allow_null=True, required=False)


class DiscountResponseSerializer(serializers.Serializer):
    """Discount details in response"""
    id = serializers.UUIDField()
    code = serializers.CharField()
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField()


class UserResponseSerializer(serializers.Serializer):
    """User details in response"""
    id = serializers.UUIDField()
    username = serializers.CharField()


class StationResponseSerializer(serializers.Serializer):
    """Station details in response"""
    id = serializers.UUIDField()
    serial_number = serializers.CharField()
    name = serializers.CharField()


class PowerBankResponseSerializer(serializers.Serializer):
    """PowerBank details in response"""
    id = serializers.UUIDField()
    serial_number = serializers.CharField()
    battery_level = serializers.IntegerField()


class TimingResponseSerializer(serializers.Serializer):
    """Timing details in response"""
    started_at = serializers.DateTimeField(allow_null=True)
    due_at = serializers.DateTimeField(allow_null=True)


class VerificationResponseSerializer(serializers.Serializer):
    """Verification status for PENDING_POPUP"""
    status = serializers.CharField()
    message = serializers.CharField()
    estimated_completion = serializers.DateTimeField(allow_null=True, required=False)


class RentalStartSuccessSerializer(serializers.Serializer):
    """
    Success response for rental start.
    Nested structure as per specification.
    """
    rental_id = serializers.UUIDField()
    rental_code = serializers.CharField()
    status = serializers.CharField()
    user = UserResponseSerializer()
    station = StationResponseSerializer()
    power_bank = PowerBankResponseSerializer(allow_null=True, required=False)
    package = PackageResponseSerializer()
    pricing = PricingResponseSerializer()
    payment = PaymentResponseSerializer()
    timing = TimingResponseSerializer()
    discount = DiscountResponseSerializer(allow_null=True, required=False)
    verification = VerificationResponseSerializer(allow_null=True, required=False)


class PaymentRequiredDataSerializer(serializers.Serializer):
    """
    Payment required response data.
    Contains payment intent and gateway details.
    """
    intent_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    shortfall = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = serializers.CharField()
    wallet_shortfall = serializers.DecimalField(max_digits=10, decimal_places=2)
    points_shortfall = serializers.IntegerField(required=False, allow_null=True)
    points_shortfall_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    postpaid_min_balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    current_balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    discount_applied = serializers.DictField(required=False, allow_null=True)
    resume_preferences = serializers.DictField(required=False, allow_null=True)
    gateway = serializers.CharField()
    payment_method_name = serializers.CharField()
    payment_method_icon = serializers.CharField(allow_null=True)
    gateway_url = serializers.CharField()
    redirect_url = serializers.CharField(allow_null=True)
    redirect_method = serializers.CharField()
    form_fields = serializers.DictField()
    payment_instructions = serializers.CharField(allow_null=True)
    expires_at = serializers.DateTimeField()
    status = serializers.CharField()
    breakdown = PaymentBreakdownSerializer(allow_null=True, required=False)


class RentalStartResponseSerializer(serializers.Serializer):
    """
    Wrapper for rental start response.
    Used for OpenAPI documentation.
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField()


class PaymentRequiredResponseSerializer(serializers.Serializer):
    """
    Payment required response.
    HTTP 402 with payment intent details.
    """
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    error_code = serializers.CharField()
    data = PaymentRequiredDataSerializer()


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standard error response.
    HTTP 4xx/5xx errors.
    """
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    error_code = serializers.CharField()
    context = serializers.DictField(required=False, allow_null=True)
