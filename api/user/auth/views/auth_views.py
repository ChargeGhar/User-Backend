"""
Authentication and OTP views
"""
import logging
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import rate_limit, log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.auth import serializers
from api.user.auth.models import User
from api.user.auth.services import AuthService, UserDeviceService, UserProfileService, AccountService

auth_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@auth_router.register(r"auth/otp/request", name="auth-otp-request")
@extend_schema(
    tags=["Authentication - OTP"],
    summary="Request OTP (Auto-detects Login/Register)",
    responses={200: BaseResponseSerializer}
)
class OTPRequestView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.OTPRequestSerializer
    permission_classes = [AllowAny]
    
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: AuthService().generate_otp(
                serializer.validated_data['identifier'],
                platform=serializer.validated_data.get('platform')
            ),
            success_message="OTP sent successfully"
        )

@auth_router.register(r"auth/otp/verify", name="auth-otp-verify")
@extend_schema(
    tags=["Authentication - OTP"],
    summary="Verify OTP",
    responses={200: BaseResponseSerializer}
)
class OTPVerifyView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.OTPVerificationSerializer
    permission_classes = [AllowAny]
    
    @rate_limit(max_requests=5, window_seconds=300)
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: AuthService().verify_otp(
                identifier=serializer.validated_data['identifier'],
                otp=serializer.validated_data['otp']
            ),
            success_message="OTP verified successfully"
        )

@auth_router.register(r"auth/complete", name="auth-complete")
@extend_schema(
    tags=["Authentication - OTP"],
    summary="Complete Authentication",
    responses={200: BaseResponseSerializer}
)
class AuthCompleteView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AuthCompleteSerializer
    permission_classes = [AllowAny]
    
    @rate_limit(max_requests=5, window_seconds=300)
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: AuthService().complete_auth(
                identifier=serializer.validated_data['identifier'],
                verification_token=str(serializer.validated_data['verification_token']),
                username=serializer.validated_data.get('username'),
                referral_code=serializer.validated_data.get('referral_code'),
                request=request
            ),
            success_message="Authentication completed successfully"
        )

@auth_router.register(r"auth/logout", name="auth-logout")
@extend_schema(
    tags=["Authentication - Session"],
    summary="User Logout",
    responses={200: BaseResponseSerializer}
)
class LogoutView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.LogoutSerializer
    
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: AuthService().logout_user(
                refresh_token=serializer.validated_data['refresh_token'],
                user=request.user,
                request=request
            ),
            success_message="Logout successful"
        )

@auth_router.register(r"auth/refresh", name="auth-refresh")
@extend_schema(
    tags=["Authentication - Session"],
    summary="Refresh JWT Access Token",
    responses={200: BaseResponseSerializer}
)
class CustomTokenRefreshView(GenericAPIView, BaseAPIView):
    serializer_class = TokenRefreshSerializer
    permission_classes = [AllowAny]
    
    @rate_limit(max_requests=10, window_seconds=300)
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: AuthService().refresh_token(
                refresh_token=serializer.validated_data.get('refresh'),
                request=request
            ),
            success_message="Token refreshed successfully"
        )

@auth_router.register(r"auth/device", name="auth-device")
@extend_schema(
    tags=["Authentication - Biometric"],
    summary="Register Device",
    responses={200: BaseResponseSerializer}
)
class DeviceView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.UserDeviceSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: UserDeviceService().register_device(
                user=request.user,
                validated_data=serializer.validated_data
            ),
            success_message="Device registered successfully"
        )

@auth_router.register(r"auth/me", name="auth-me")
@extend_schema(
    tags=["Authentication - Profile"],
    summary="Current User Complete Info",
    responses={200: BaseResponseSerializer}
)
class MeView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.UserDetailedProfileSerializer
    permission_classes = [IsAuthenticated]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get comprehensive real-time user data via service layer"""
        return self.handle_service_operation(
            lambda: self.get_serializer(
                UserProfileService().get_detailed_profile(request.user)
            ).data,
            success_message="User data retrieved successfully"
        )

@auth_router.register(r"auth/account", name="auth-account")
@extend_schema(
    tags=["Authentication - Profile"],
    summary="Delete Account",
    description="Soft-deletes the authenticated user account. PII is anonymized and the account is deactivated. Financial records (transactions, rentals, etc.) are preserved.",
    responses={200: BaseResponseSerializer}
)
class DeleteAccountView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserSerializer
    
    @log_api_call()
    def delete(self, request: Request) -> Response:
        def operation():
            AccountService().delete_account(user=request.user, request=request)
            return {'message': 'Account deleted successfully'}
        return self.handle_service_operation(
            operation,
            success_message="Account deleted successfully"
        )
