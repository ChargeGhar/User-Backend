from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from typing import Dict, Any
from api.users.models import User, UserProfile

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
        read_only_fields = ['id', 'referral_code', 'status', 'date_joined']
    
    @extend_schema_field(serializers.BooleanField)
    def get_profile_complete(self, obj) -> bool:
        try:
            return obj.profile.is_profile_complete if hasattr(obj, 'profile') and obj.profile else False
        except:
            return False
    
    @extend_schema_field(serializers.CharField)
    def get_kyc_status(self, obj) -> str:
        try:
            return obj.kyc.status if hasattr(obj, 'kyc') and obj.kyc else 'NOT_SUBMITTED'
        except:
            return 'NOT_SUBMITTED'
    
    @extend_schema_field(serializers.DictField)
    def get_profile(self, obj) -> dict:
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
        return {'full_name': None, 'date_of_birth': None, 'address': None, 'is_profile_complete': False}

class UserDetailedProfileSerializer(serializers.Serializer):
    """Comprehensive serializer for /me endpoint with all user-related data"""
    id = serializers.CharField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    profile_picture = serializers.URLField(allow_null=True)
    referral_code = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    social_provider = serializers.CharField()
    date_joined = serializers.DateTimeField()
    
    profile = serializers.DictField()
    kyc = serializers.DictField()
    wallet = serializers.DictField()
    points = serializers.DictField()
    rental_eligibility = serializers.DictField()

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info serializer"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'profile_picture']
