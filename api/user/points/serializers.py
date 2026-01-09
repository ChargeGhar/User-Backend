from __future__ import annotations

from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field

from api.user.points.models import PointsTransaction, Referral, UserPoints
from api.user.auth.models import User
from api.common.utils.helpers import convert_points_to_amount
from api.common.serializers import BaseResponseSerializer


# MVP Pattern: List vs Detail Serializers

class PointsTransactionListSerializer(serializers.ModelSerializer):
    """Minimal serializer for points transaction lists - MVP optimized"""
    formatted_points = serializers.SerializerMethodField()
    
    class Meta:
        model = PointsTransaction
        fields = [
            'id', 'transaction_type', 'source', 'points', 
            'description', 'created_at', 'formatted_points'
        ]
        read_only_fields = ['id', 'created_at']
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_points(self, obj) -> str:
        """Get formatted points display"""
        sign = "+" if obj.transaction_type == 'EARNED' else "-"
        return f"{sign}{abs(obj.points)} points"


class PointsTransactionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for points transactions - Full data"""
    points_value = serializers.SerializerMethodField()
    formatted_points = serializers.SerializerMethodField()
    rental_code = serializers.CharField(source='related_rental.rental_code', read_only=True)
    
    class Meta:
        model = PointsTransaction
        fields = [
            'id', 'transaction_type', 'source', 'points', 'balance_before',
            'balance_after', 'description', 'created_at', 'points_value',
            'formatted_points', 'rental_code', 'metadata'
        ]
        read_only_fields = ['id', 'created_at']
    
    @extend_schema_field(serializers.FloatField)
    def get_points_value(self, obj) -> float:
        """Get monetary value of points"""
        return float(convert_points_to_amount(abs(obj.points)))
    
    @extend_schema_field(serializers.CharField)
    def get_formatted_points(self, obj) -> str:
        """Get formatted points display"""
        sign = "+" if obj.transaction_type == 'EARNED' else "-"
        return f"{sign}{abs(obj.points)} points"


# Backward compatibility alias
PointsTransactionSerializer = PointsTransactionDetailSerializer


class UserPointsSerializer(serializers.ModelSerializer):
    """Serializer for user points"""
    points_value = serializers.SerializerMethodField()
    formatted_current_points = serializers.SerializerMethodField()
    formatted_total_points = serializers.SerializerMethodField()
    
    class Meta:
        model = UserPoints
        fields = [
            'current_points', 'total_points', 'last_updated',
            'points_value', 'formatted_current_points', 'formatted_total_points'
        ]
        read_only_fields = ['last_updated']
    
    def get_points_value(self, obj):
        """Get monetary value of current points"""
        return float(convert_points_to_amount(obj.current_points))
    
    def get_formatted_current_points(self, obj):
        return f"{obj.current_points:,} points"
    
    def get_formatted_total_points(self, obj):
        return f"{obj.total_points:,} points"


class ReferralListSerializer(serializers.ModelSerializer):
    """Minimal serializer for referral lists - MVP optimized"""
    invitee_username = serializers.CharField(source='invitee.username', read_only=True)
    status = serializers.ChoiceField(
        choices=Referral.STATUS_CHOICES,
        help_text="Referral status"
    )
    
    class Meta:
        model = Referral
        fields = [
            'id', 'status', 'invitee_username', 'inviter_points_awarded',
            'invitee_points_awarded', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'status']


class ReferralDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for referrals - Full data"""
    inviter_username = serializers.CharField(source='inviter.username', read_only=True)
    invitee_username = serializers.CharField(source='invitee.username', read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    status = serializers.ChoiceField(
        choices=Referral.STATUS_CHOICES,
        help_text="Referral status"
    )
    
    class Meta:
        model = Referral
        fields = [
            'id', 'referral_code', 'status', 'inviter_points_awarded',
            'invitee_points_awarded', 'first_rental_completed', 'completed_at',
            'expires_at', 'created_at', 'inviter_username', 'invitee_username',
            'is_expired', 'days_until_expiry'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at', 'status']
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_expired(self, obj) -> bool:
        return timezone.now() > obj.expires_at
    
    def get_days_until_expiry(self, obj):
        if timezone.now() > obj.expires_at:
            return 0
        delta = obj.expires_at - timezone.now()
        return delta.days


# Backward compatibility alias
ReferralSerializer = ReferralDetailSerializer





class ReferralClaimSerializer(serializers.Serializer):
    """Serializer for claiming referral rewards"""
    referral_code = serializers.CharField(required=True)


class PointsHistoryFilterSerializer(serializers.Serializer):
    """Serializer for points history filters"""
    transaction_type = serializers.ChoiceField(
        choices=PointsTransaction.TRANSACTION_TYPE_CHOICES,
        required=False
    )
    source = serializers.ChoiceField(
        choices=PointsTransaction.SOURCE_CHOICES,
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


class PointsSummarySerializer(serializers.Serializer):
    """Serializer for comprehensive points overview"""
    current_points = serializers.IntegerField()
    total_points_earned = serializers.IntegerField()
    total_points_spent = serializers.IntegerField()
    points_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Breakdown by source
    points_from_signup = serializers.IntegerField()
    points_from_referrals = serializers.IntegerField()
    points_from_topups = serializers.IntegerField()
    points_from_rentals = serializers.IntegerField()
    points_from_timely_returns = serializers.IntegerField()
    points_from_coupons = serializers.IntegerField()
    
    # Recent activity
    recent_transactions_count = serializers.IntegerField()
    last_earned_date = serializers.DateTimeField(allow_null=True)
    last_spent_date = serializers.DateTimeField(allow_null=True)
    
    # Referral stats
    total_referrals_sent = serializers.IntegerField()
    successful_referrals = serializers.IntegerField()
    pending_referrals = serializers.IntegerField()
    referral_points_earned = serializers.IntegerField()


class PointsLeaderboardListSerializer(serializers.Serializer):
    """Minimal serializer for leaderboard lists - MVP optimized"""
    rank = serializers.IntegerField()
    username = serializers.CharField()
    total_points = serializers.IntegerField()
    points_this_month = serializers.IntegerField()


class PointsLeaderboardDetailSerializer(serializers.Serializer):
    """Detailed serializer for leaderboard - Full data"""
    rank = serializers.IntegerField()
    user_id = serializers.UUIDField()
    username = serializers.CharField()
    total_points = serializers.IntegerField()
    current_points = serializers.IntegerField()
    points_this_month = serializers.IntegerField()
    referrals_count = serializers.IntegerField()
    rentals_count = serializers.IntegerField()


# Backward compatibility alias
PointsLeaderboardSerializer = PointsLeaderboardDetailSerializer





# Response Serializers for Swagger Documentation

class PointsHistoryResponseSerializer(BaseResponseSerializer):
    """Response serializer for points history endpoint"""
    class PointsHistoryDataSerializer(serializers.Serializer):
        results = PointsTransactionListSerializer(many=True)
        pagination = serializers.DictField()
    
    data = PointsHistoryDataSerializer()


class PointsSummaryResponseSerializer(BaseResponseSerializer):
    """Response serializer for points summary endpoint"""
    data = PointsSummarySerializer()


class UserReferralCodeResponseSerializer(BaseResponseSerializer):
    """Response serializer for user referral code endpoint"""
    class ReferralCodeDataSerializer(serializers.Serializer):
        referral_code = serializers.CharField()
        user_id = serializers.UUIDField()
        username = serializers.CharField()
    
    data = ReferralCodeDataSerializer()





class ReferralClaimResponseSerializer(BaseResponseSerializer):
    """Response serializer for referral claim endpoint"""
    class ClaimDataSerializer(serializers.Serializer):
        points_awarded = serializers.IntegerField()
        referral_id = serializers.UUIDField()
        completed_at = serializers.DateTimeField()
        validation_passed = serializers.BooleanField()
    
    data = ClaimDataSerializer()


class UserReferralsResponseSerializer(BaseResponseSerializer):
    """Response serializer for user referrals endpoint"""
    class UserReferralsDataSerializer(serializers.Serializer):
        results = ReferralListSerializer(many=True)
        pagination = serializers.DictField()
    
    data = UserReferralsDataSerializer()


class PointsLeaderboardResponseSerializer(BaseResponseSerializer):
    """Response serializer for points leaderboard endpoint"""
    data = PointsLeaderboardListSerializer(many=True)



