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
from api.user.auth import serializers
from api.user.auth.services import UserKYCService, UserProfileService

profile_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@profile_router.register(r"users/profile", name="user-profile")
@extend_schema(
    tags=["Authentication"],
    summary="User Profile Management",
    responses={200: BaseResponseSerializer}
)
class UserProfileView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user profile - fresh from DB"""
        profile = UserProfileService().profile_repo.get_by_user_id(request.user.id)
        if not profile:
            profile = UserProfileService().profile_repo.create_profile(user=request.user)
            
        return self.handle_service_operation(
            lambda: self.get_serializer(profile).data,
            success_message="Profile retrieved successfully"
        )
    
    @log_api_call()
    def put(self, request: Request) -> Response:
        """Update user profile (full update)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: self.get_serializer(
                UserProfileService().update_profile(request.user, serializer.validated_data)
            ).data,
            success_message="Profile updated successfully"
        )
    
    @log_api_call()
    def patch(self, request: Request) -> Response:
        """Partial update user profile"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: self.get_serializer(
                UserProfileService().update_profile(request.user, serializer.validated_data)
            ).data,
            success_message="Profile updated successfully"
        )

@profile_router.register(r"users/kyc", name="user-kyc")
@extend_schema(
    tags=["Authentication"],
    summary="KYC Document Submission",
    responses={201: BaseResponseSerializer}
)
class UserKYCView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.UserKYCSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: self.get_serializer(
                UserKYCService().submit_kyc(request.user, serializer.validated_data)
            ).data,
            success_message="KYC documents submitted successfully",
            success_status=status.HTTP_201_CREATED
        )
    
    @log_api_call()
    def patch(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: self.get_serializer(
                UserKYCService().submit_kyc(request.user, serializer.validated_data)
            ).data,
            success_message="KYC documents updated successfully"
        )

@profile_router.register(r"users/kyc/status", name="user-kyc-status")
@extend_schema(
    tags=["Authentication"],
    summary="KYC Status",
    responses={200: BaseResponseSerializer}
)
class UserKYCStatusView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserKYCSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        return self.handle_service_operation(
            lambda: UserKYCService().get_kyc_status(request.user),
            success_message="KYC status retrieved successfully"
        )

@profile_router.register(r"users/wallet", name="user-wallet")
@extend_schema(
    tags=["Authentication"],
    summary="User Wallet",
    responses={200: BaseResponseSerializer}
)
class UserWalletView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserWalletResponseSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        return self.handle_service_operation(
            lambda: UserProfileService().get_wallet_summary(request.user),
            success_message="Wallet information retrieved successfully"
        )

@profile_router.register(r"users/analytics/usage-stats", name="user-analytics")
@extend_schema(
    tags=["Authentication"],
    summary="User Analytics",
    responses={200: BaseResponseSerializer}
)
class UserAnalyticsView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.UserAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        return self.handle_service_operation(
            lambda: UserProfileService().get_user_analytics(request.user),
            success_message="Analytics retrieved successfully"
        )
