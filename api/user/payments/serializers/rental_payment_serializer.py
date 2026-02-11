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
    PAYMENT_MODE_CHOICES = [
        ('wallet', 'Wallet'),
        ('points', 'Points'),
        ('wallet_points', 'Wallet + Points'),
        ('direct', 'Direct Gateway Payment'),
    ]
    scenario = serializers.ChoiceField(choices=SCENARIO_CHOICES)
    package_id = serializers.UUIDField(required=False, allow_null=True)
    rental_id = serializers.UUIDField(required=False, allow_null=True)
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True
    )
    payment_mode = serializers.ChoiceField(
        choices=PAYMENT_MODE_CHOICES,
        required=False,
        default='wallet_points'
    )
    wallet_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True
    )
    points_to_use = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True
    )

    def validate(self, attrs):
        scenario = attrs.get('scenario')
        package_id = attrs.get('package_id')
        rental_id = attrs.get('rental_id')
        payment_mode = attrs.get('payment_mode', 'wallet_points')
        wallet_amount = attrs.get('wallet_amount')
        points_to_use = attrs.get('points_to_use')

        if scenario == 'pre_payment' and not package_id:
            raise serializers.ValidationError({'package_id': 'package_id is required for pre_payment'})

        if scenario == 'post_payment' and not rental_id:
            raise serializers.ValidationError({'rental_id': 'rental_id is required for post_payment'})

        if (wallet_amount is None) ^ (points_to_use is None):
            raise serializers.ValidationError(
                {'wallet_points_split': 'Provide both wallet_amount and points_to_use together'}
            )

        if payment_mode != 'wallet_points' and (wallet_amount is not None or points_to_use is not None):
            raise serializers.ValidationError(
                {'wallet_points_split': 'wallet_amount and points_to_use are only valid for wallet_points mode'}
            )

        return attrs

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
