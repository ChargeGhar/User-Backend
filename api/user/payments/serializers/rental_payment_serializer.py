from rest_framework import serializers
from api.user.rentals.models import RentalPackage

class RentalPackageSerializer(serializers.ModelSerializer):
    """Serializer for rental packages"""
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = RentalPackage
        fields = [
            'id', 'name', 'description', 'duration_minutes', 'price',
            'package_type', 'payment_model', 'is_active', 'duration_display'
        ]
    
    def get_duration_display(self, obj) -> str:
        minutes = obj.duration_minutes
        if minutes < 60:
            return f"{minutes} minutes"
        elif minutes < 1440:
            hours = minutes // 60
            rem = minutes % 60
            return f"{hours}h {rem}m" if rem else f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            days = minutes // 1440
            return f"{days} day{'s' if days > 1 else ''}"

class CalculatePaymentOptionsSerializer(serializers.Serializer):
    """Serializer for calculating payment options"""
    SCENARIO_CHOICES = [
        ('pre_payment', 'Pre-payment'),
        ('post_payment', 'Post-payment'),
    ]
    scenario = serializers.ChoiceField(choices=SCENARIO_CHOICES)
    package_id = serializers.UUIDField(required=False, allow_null=True)
    rental_id = serializers.UUIDField(required=False, allow_null=True)

class PaymentOptionsResponseSerializer(serializers.Serializer):
    """Serializer for payment options response"""
    scenario = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    user_balances = serializers.DictField()
    payment_breakdown = serializers.DictField()
    is_sufficient = serializers.BooleanField()
    shortfall = serializers.DecimalField(max_digits=10, decimal_places=2)
    suggested_topup = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)

class PayDueSerializer(serializers.Serializer):
    """Serializer for paying rental dues"""
    use_points = serializers.BooleanField(default=True)
    use_wallet = serializers.BooleanField(default=True)
