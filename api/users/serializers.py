from __future__ import annotations

from typing import Dict, Any, Optional
from rest_framework import serializers
# Removed password-related imports for OTP-based authentication
from drf_spectacular.utils import extend_schema_field

from api.users.models import User, UserProfile, UserKYC, UserDevice
from api.points.models import UserPoints
from api.common.utils.helpers import validate_phone_number, mask_sensitive_data

class OTPRequestSerializer(serializers.Serializer):
    """Serializer for OTP request - automatically detects login vs register"""
    identifier = serializers.CharField(help_text="Email or phone number")
    
    def validate_identifier(self, value):
        # Basic validation for email or phone format
        if '@' in value:
            # Email validation
            try:
                serializers.EmailField().run_validation(value)
            except serializers.ValidationError:
                raise serializers.ValidationError("Invalid email format")
        else:
            # Phone validation
            if not validate_phone_number(value):
                raise serializers.ValidationError("Invalid phone number format")
        
        return value


class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    identifier = serializers.CharField(help_text="Email or phone number")
    otp = serializers.CharField(max_length=6, min_length=6)


class AuthCompleteSerializer(serializers.Serializer):
    """Serializer for authentication completion"""
    identifier = serializers.CharField(help_text="Email or phone number")
    verification_token = serializers.UUIDField(help_text="Token from OTP verification")
    username = serializers.CharField(
        max_length=150, 
        required=False,
        help_text="Required only for new user registration"
    )
    referral_code = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        help_text="Referral code from another user (optional)"
    )
    
    def validate_username(self, value):
        """Validate username format and uniqueness"""
        if value:
            # Check format
            if len(value.strip()) < 3:
                raise serializers.ValidationError("Username must be at least 3 characters")
            
            # Check uniqueness
            from api.users.models import User
            if User.objects.filter(username=value.strip()).exists():
                raise serializers.ValidationError("Username already exists")
        
        return value.strip() if value else value


class LogoutSerializer(serializers.Serializer):
    """Serializer for user logout"""
    refresh_token = serializers.CharField(help_text="JWT refresh token to blacklist")
    
    def validate_refresh_token(self, value):
        """Validate refresh token format"""
        if not value or not value.strip():
            raise serializers.ValidationError("Refresh token is required")
        return value.strip()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'full_name', 'date_of_birth', 'address', 
            'avatar_url', 'is_profile_complete', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_profile_complete', 'created_at', 'updated_at']
    
    def validate_full_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters")
        return value.strip() if value else value


class UserKYCSerializer(serializers.ModelSerializer):
    """Serializer for user KYC"""
    
    class Meta:
        model = UserKYC
        fields = [
            'id', 'document_type', 'document_number', 'document_front_url',
            'document_back_url', 'status', 'verified_at', 'rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'verified_at', 'rejection_reason', 
            'created_at', 'updated_at'
        ]
    
    def validate_document_number(self, value):
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError("Document number must be at least 5 characters")
        return value.strip()


class UserDeviceSerializer(serializers.ModelSerializer):
    """Serializer for user device registration"""
    
    class Meta:
        model = UserDevice
        fields = [
            'id', 'device_id', 'fcm_token', 'device_type', 'device_name',
            'app_version', 'os_version', 'is_active', 'last_used'
        ]
        read_only_fields = ['id', 'last_used']
    
    def validate_fcm_token(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Invalid FCM token")
        return value.strip()


class UserSerializer(serializers.ModelSerializer):
    """Standard user serializer with essential real-time data"""
    profile_complete = serializers.SerializerMethodField()
    kyc_status = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'username', 'profile_picture', 'referral_code', 
            'status', 'is_active', 'date_joined', 'last_login', 
            'profile_complete', 'kyc_status', 'profile', 'social_provider'
        ]
        read_only_fields = [
            'id', 'referral_code', 'status', 'date_joined'
        ]
    
    @extend_schema_field(serializers.BooleanField)
    def get_profile_complete(self, obj) -> bool:
        """Check if profile is complete - real-time from DB"""
        try:
            # Use select_related to avoid N+1 queries
            if hasattr(obj, '_prefetched_objects_cache') and 'profile' in obj._prefetched_objects_cache:
                return obj.profile.is_profile_complete if obj.profile else False
            return obj.profile.is_profile_complete if hasattr(obj, 'profile') and obj.profile else False
        except:
            return False
    
    @extend_schema_field(serializers.CharField)
    def get_kyc_status(self, obj) -> str:
        """Get KYC status - real-time from DB"""
        try:
            # Use select_related to avoid N+1 queries
            if hasattr(obj, '_prefetched_objects_cache') and 'kyc' in obj._prefetched_objects_cache:
                return obj.kyc.status if obj.kyc else 'NOT_SUBMITTED'
            return obj.kyc.status if hasattr(obj, 'kyc') and obj.kyc else 'NOT_SUBMITTED'
        except:
            return 'NOT_SUBMITTED'
    
    @extend_schema_field(serializers.DictField)
    def get_profile(self, obj) -> dict:
        """Get profile data"""
        try:
            if hasattr(obj, 'profile') and obj.profile:
                return {
                    'full_name': obj.profile.full_name,
                    'date_of_birth': obj.profile.date_of_birth,
                    'address': obj.profile.address,
                    'is_profile_complete': obj.profile.is_profile_complete
                }
        except:
            pass
        return {
            'full_name': None,
            'date_of_birth': None,
            'address': None,
            'is_profile_complete': False
        }


class UserDetailedProfileSerializer(serializers.Serializer):
    """Comprehensive serializer for /me endpoint with all user-related data"""
    # User basic info
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    profile_picture = serializers.URLField(allow_null=True)
    referral_code = serializers.CharField()
    status = serializers.CharField()
    social_provider = serializers.CharField()
    date_joined = serializers.DateTimeField()
    
    # Profile data
    profile = serializers.SerializerMethodField()
    
    # KYC data
    kyc = serializers.SerializerMethodField()
    
    # Wallet data
    wallet = serializers.SerializerMethodField()
    
    # Points data
    points = serializers.SerializerMethodField()
    
    # Rental requirements status
    rental_eligibility = serializers.SerializerMethodField()
    
    @extend_schema_field(serializers.DictField)
    def get_profile(self, obj) -> Dict[str, Any]:
        """Get profile data - compact format"""
        try:
            profile = obj.profile
            return {
                'full_name': profile.full_name,
                'date_of_birth': profile.date_of_birth,
                'address': profile.address,
                'avatar_url': profile.avatar_url,
                'completed': profile.is_profile_complete
            }
        except:
            return {
                'full_name': None,
                'date_of_birth': None,
                'address': None,
                'avatar_url': None,
                'completed': False
            }
    
    @extend_schema_field(serializers.DictField)
    def get_kyc(self, obj) -> Dict[str, Any]:
        """Get KYC data - detailed format with all KYC fields"""
        try:
            kyc = obj.kyc
            return {
                'document_number': kyc.document_number,
                'document_front_url': kyc.document_front_url,
                'document_back_url': kyc.document_back_url,
                'document_type': kyc.document_type,
                'status': kyc.status,
                'verified_at': kyc.verified_at,
                'rejection_reason': kyc.rejection_reason,
                'verified': kyc.status == 'APPROVED'
            }
        except:
            return {
                'document_number': None,
                'document_front_url': None,
                'document_back_url': None,
                'document_type': None,
                'status': 'NOT_SUBMITTED',
                'verified_at': None,
                'rejection_reason': None,
                'verified': False
            }
    
    @extend_schema_field(serializers.DictField)
    def get_wallet(self, obj) -> Dict[str, Any]:
        """Get wallet data - fresh from DB, compact format"""
        try:
            from api.payments.models import Wallet, Transaction
            from django.db.models import Sum
            
            wallet = Wallet.objects.get(user=obj)
            
            # Calculate total successful topups
            total_topup = Transaction.objects.filter(
                user=obj,
                transaction_type='TOPUP',
                status='SUCCESS'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            return {
                'balance': str(wallet.balance),
                'total_topup': str(total_topup),
                'currency': wallet.currency
            }
        except:
            return {
                'balance': '0.00',
                'total_topup': '0.00',
                'currency': 'NPR'
            }
    
    @extend_schema_field(serializers.DictField)
    def get_points(self, obj) -> Dict[str, Any]:
        """Get points data - fresh from DB, compact format"""
        try:
            points = obj.points
            return {
                'current': points.current_points,
                'total_earned': points.total_points
            }
        except:
            return {
                'current': 0,
                'total_earned': 0
            }
    
    @extend_schema_field(serializers.DictField)
    def get_rental_eligibility(self, obj) -> Dict[str, Any]:
        """Check rental eligibility - compact format"""
        from api.system.services.app_config_service import AppConfigService
        
        config_service = AppConfigService()
        
        # Check requirements from app config
        need_profile = config_service.get_config_cached('NEED_RENTALS_PROFILE_COMPLETE', 'true').lower() in ['true', '1', 'yes']
        need_kyc = config_service.get_config_cached('NEED_RENTALS_KYC_VERIFIED', 'true').lower() in ['true', '1', 'yes']
        
        # Get actual status
        try:
            profile_complete = obj.profile.is_profile_complete if hasattr(obj, 'profile') and obj.profile else False
        except:
            profile_complete = False
        
        try:
            kyc_verified = obj.kyc.status == 'APPROVED' if hasattr(obj, 'kyc') and obj.kyc else False
        except:
            kyc_verified = False
        
        # Check if active
        is_active = obj.status == 'ACTIVE'
        
        # Check for pending dues
        from api.rentals.models import Rental
        has_pending_dues = Rental.objects.filter(
            user=obj,
            payment_status='PENDING',
            status__in=['OVERDUE', 'COMPLETED']
        ).exists()
        
        # Determine eligibility
        can_rent = (
            is_active and
            not has_pending_dues and
            (not need_profile or profile_complete) and
            (not need_kyc or kyc_verified)
        )
        
        # Build blocking reasons
        reasons = []
        if not is_active:
            reasons.append('Account not active')
        if has_pending_dues:
            reasons.append('Pending dues')
        if need_profile and not profile_complete:
            reasons.append('Complete profile')
        if need_kyc and not kyc_verified:
            reasons.append('Verify KYC')
        
        return {
            'can_rent': can_rent,
            'reasons': reasons
        }


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info serializer"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'profile_picture']


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


# Password change removed - OTP-based authentication only
class UserFilterSerializer(serializers.Serializer):
    """Serializer for user filtering parameters"""
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    status = serializers.ChoiceField(choices=User.STATUS_CHOICES, required=False)
    email_verified = serializers.BooleanField(required=False)
    phone_verified = serializers.BooleanField(required=False)
    search = serializers.CharField(required=False, max_length=255)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    
    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date cannot be after end_date")
        
        return attrs
