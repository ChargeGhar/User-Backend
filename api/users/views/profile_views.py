"""
User profile and KYC views
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.users import serializers
from api.users.services import UserKYCService, UserProfileService

profile_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@profile_router.register(r"users/profile", name="user-profile")
@extend_schema(
    tags=["Authentication"],
    summary="User Profile Management",
    description="Get and update user profile with real-time data. Profile completion awards points.",
    responses={200: BaseResponseSerializer}
)
class UserProfileView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user profile - fresh from DB"""
        def operation():
            try:
                # Get fresh profile data
                from api.users.models import UserProfile
                profile = UserProfile.objects.get(user=request.user)
                serializer = self.get_serializer(profile)
                return serializer.data
            except UserProfile.DoesNotExist:
                # Return empty profile structure if not found
                return {
                    'id': None,
                    'full_name': None,
                    'date_of_birth': None,
                    'address': None,
                    'avatar_url': None,
                    'is_profile_complete': False,
                    'created_at': None,
                    'updated_at': None
                }
        
        return self.handle_service_operation(
            operation,
            success_message="Profile retrieved successfully",
            error_message="Failed to retrieve profile"
        )
    
    @log_api_call()
    def put(self, request: Request) -> Response:
        """Update user profile (full update)"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            profile_service = UserProfileService()
            profile = profile_service.update_profile(
                user=request.user,
                validated_data=serializer.validated_data
            )
            response_serializer = self.get_serializer(profile)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Profile updated successfully",
            error_message="Failed to update profile"
        )
    
    @log_api_call()
    def patch(self, request: Request) -> Response:
        """Partial update user profile"""
        def operation():
            serializer = self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            profile_service = UserProfileService()
            profile = profile_service.update_profile(
                user=request.user,
                validated_data=serializer.validated_data
            )
            response_serializer = self.get_serializer(profile)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Profile updated successfully",
            error_message="Failed to update profile"
        )

@profile_router.register(r"users/kyc", name="user-kyc")
@extend_schema(
    tags=["Authentication"],
    summary="KYC Document Submission",
    description="Upload KYC documents for verification",
    responses={201: BaseResponseSerializer}
)
class UserKYCView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.UserKYCSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Submit KYC documents"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            kyc_service = UserKYCService()
            kyc = kyc_service.submit_kyc(
                user=request.user,
                validated_data=serializer.validated_data
            )
            response_serializer = self.get_serializer(kyc)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="KYC documents submitted successfully",
            error_message="Failed to submit KYC documents",
            success_status=status.HTTP_201_CREATED
        )
    
    @log_api_call()
    def patch(self, request: Request) -> Response:
        """Update KYC documents"""
        def operation():
            serializer = self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            kyc_service = UserKYCService()
            kyc = kyc_service.submit_kyc(
                user=request.user,
                validated_data=serializer.validated_data
            )
            response_serializer = self.get_serializer(kyc)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="KYC documents updated successfully",
            error_message="Failed to update KYC documents"
        )

@profile_router.register(r"users/kyc/status", name="user-kyc-status")
@extend_schema(
    tags=["Authentication"],
    summary="KYC Status",
    description="Returns real-time KYC verification status",
    responses={200: BaseResponseSerializer}
)
class UserKYCStatusView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserKYCSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get real-time KYC status"""
        def operation():
            try:
                # Get fresh KYC data from DB
                kyc = request.user.kyc
                return {
                    'status': kyc.status,
                    'submitted_at': kyc.created_at,
                    'verified_at': kyc.verified_at,
                    'rejection_reason': kyc.rejection_reason
                }
            except:
                return {
                    'status': 'NOT_SUBMITTED',
                    'submitted_at': None,
                    'verified_at': None,
                    'rejection_reason': None
                }
        
        return self.handle_service_operation(
            operation,
            success_message="KYC status retrieved successfully",
            error_message="Failed to retrieve KYC status"
        )

@profile_router.register(r"users/wallet", name="user-wallet")
@extend_schema(
    tags=["Authentication"],
    summary="User Wallet",
    description="Display real-time wallet balance and points",
    responses={200: BaseResponseSerializer}
)
class UserWalletView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserWalletResponseSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get real-time wallet data - no caching for financial data"""
        def operation():
            user = request.user
            
            # Get fresh wallet balance from DB
            try:
                # Force fresh query for financial data
                from api.payments.models import Wallet
                wallet = Wallet.objects.get(user=user)
                wallet_balance = str(wallet.balance)
                currency = wallet.currency
                last_updated = wallet.updated_at
            except Wallet.DoesNotExist:
                # Create wallet if doesn't exist
                from api.payments.models import Wallet
                wallet = Wallet.objects.create(user=user)
                wallet_balance = '0.00'
                currency = 'NPR'
                last_updated = wallet.created_at
            
            # Get fresh points from DB
            try:
                from api.points.models import UserPoints
                points = UserPoints.objects.get(user=user)
                current_points = points.current_points
                total_points = points.total_points
            except UserPoints.DoesNotExist:
                # Create points if doesn't exist
                from api.points.models import UserPoints
                points = UserPoints.objects.create(user=user)
                current_points = 0
                total_points = 0
            
            return {
                'balance': wallet_balance,
                'currency': currency,
                'last_updated': last_updated,
                'points': {
                    'current_points': current_points,
                    'total_points': total_points
                }
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Wallet information retrieved successfully",
            error_message="Failed to retrieve wallet information"
        )

@profile_router.register(r"users/analytics/usage-stats", name="user-analytics")
@extend_schema(
    tags=["Authentication"],
    summary="User Analytics",
    description="Provides real-time usage statistics and analytics",
    responses={200: BaseResponseSerializer}
)
class UserAnalyticsView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.UserAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get real-time analytics data"""
        def operation():
            profile_service = UserProfileService()
            # Get fresh analytics data from DB
            analytics = profile_service.get_user_analytics(request.user)
            serializer = self.get_serializer(analytics)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Analytics retrieved successfully",
            error_message="Failed to retrieve analytics"
        )