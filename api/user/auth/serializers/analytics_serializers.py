from rest_framework import serializers

class UserAnalyticsSerializer(serializers.Serializer):
    """Serializer for user analytics data"""
    total_rentals = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_points_earned = serializers.IntegerField()
    total_referrals = serializers.IntegerField()
    timely_returns = serializers.IntegerField()
    late_returns = serializers.IntegerField()
    favorite_stations_count = serializers.IntegerField()
    last_rental_date = serializers.DateTimeField(allow_null=True)
    member_since = serializers.DateTimeField()

class UserWalletResponseSerializer(serializers.Serializer):
    """MVP serializer for wallet response - real-time data"""
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='NPR')
    points = serializers.DictField()
    last_updated = serializers.DateTimeField(read_only=True)

class UserFilterSerializer(serializers.Serializer):
    """Serializer for user filtering parameters"""
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    search = serializers.CharField(required=False, max_length=255)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    
    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date cannot be after end_date")
        return attrs
