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
    ALLOWED_INPUT_FIELDS = {
        'package_id',
        'rental_id',
        'payment_mode',
        'wallet_amount',
        'points_to_use',
    }
    PAYMENT_MODE_CHOICES = [
        ('wallet', 'Wallet'),
        ('points', 'Points'),
        ('wallet_points', 'Wallet + Points'),
        ('direct', 'Direct Gateway Payment'),
    ]
    package_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Pre-payment context: provide package_id",
    )
    rental_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Post-payment context: provide rental_id",
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
        unknown_fields = set(self.initial_data.keys()) - self.ALLOWED_INPUT_FIELDS
        if unknown_fields:
            raise serializers.ValidationError(
                {'unsupported_fields': [f'Unsupported field: {field}' for field in sorted(unknown_fields)]}
            )

        package_id = attrs.get('package_id')
        rental_id = attrs.get('rental_id')
        payment_mode = attrs.get('payment_mode', 'wallet_points')
        wallet_amount = attrs.get('wallet_amount')
        points_to_use = attrs.get('points_to_use')

        if package_id and rental_id:
            raise serializers.ValidationError(
                {'selector': 'Provide either package_id or rental_id, not both'}
            )
        if not package_id and not rental_id:
            raise serializers.ValidationError(
                {'selector': 'Either package_id or rental_id is required'}
            )

        if (wallet_amount is None) ^ (points_to_use is None):
            raise serializers.ValidationError(
                {'wallet_points_split': 'Provide both wallet_amount and points_to_use together'}
            )

        if payment_mode != 'wallet_points' and (wallet_amount is not None or points_to_use is not None):
            raise serializers.ValidationError(
                {'wallet_points_split': 'wallet_amount and points_to_use are only valid for wallet_points mode'}
            )

        attrs['scenario'] = 'pre_payment' if package_id else 'post_payment'
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
