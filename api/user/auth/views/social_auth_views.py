"""
Social authentication views
"""
import logging
import os
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer

social_router = CustomViewRouter()
logger = logging.getLogger(__name__)


class SocialAuthMixin:
    """Mixin for common social authentication functionality"""
    
    @staticmethod
    def get_frontend_url() -> str:
        """Get frontend URL from environment"""
        return os.getenv('FRONTEND_URL', 'https://chargeghar.app')
    
    @staticmethod
    def build_frontend_redirect(status: str, **params) -> Response:
        """Build frontend redirect URL with query parameters"""
        frontend_url = SocialAuthMixin.get_frontend_url()
        query_params = urlencode({'status': status, **params})
        return redirect(f"{frontend_url}/social/login-status?{query_params}")
    
    @staticmethod
    def get_user_provider(user) -> str:
        """Get social provider for authenticated user"""
        try:
            socialaccount = getattr(user, 'socialaccount_set', None)
            if socialaccount and socialaccount.exists():
                return socialaccount.first().provider
        except Exception as e:
            logger.debug(f"Could not determine provider: {e}")
        return 'google'  # default


@social_router.register(r"auth/google/login", name="auth-google-login")
@extend_schema(
    tags=["Authentication"],
    summary="Google OAuth Login",
    description="Get Google OAuth login URL (uses django-allauth)",
    responses={200: BaseResponseSerializer}
)
class GoogleLoginView(GenericAPIView, BaseAPIView):
    permission_classes = [AllowAny]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get Google OAuth login URL"""
        def operation():
            google_login_url = request.build_absolute_uri(reverse('google_login'))
            return {
                'login_url': google_login_url,
                'message': 'Redirect user to this URL for Google OAuth',
                'provider': 'google'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Google OAuth URL retrieved",
            error_message="Failed to get Google OAuth URL"
        )


@social_router.register(r"auth/apple/login", name="auth-apple-login")
@extend_schema(
    tags=["Authentication"],
    summary="Apple OAuth Login",
    description="Get Apple OAuth login URL (uses django-allauth)",
    responses={200: BaseResponseSerializer}
)
class AppleLoginView(GenericAPIView, BaseAPIView):
    permission_classes = [AllowAny]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get Apple OAuth login URL"""
        def operation():
            apple_login_url = request.build_absolute_uri(reverse('apple_login'))
            return {
                'login_url': apple_login_url,
                'message': 'Redirect user to this URL for Apple OAuth',
                'provider': 'apple'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Apple OAuth URL retrieved",
            error_message="Failed to get Apple OAuth URL"
        )


@social_router.register(r"auth/social/success", name="auth-social-success")
@extend_schema(
    tags=["Authentication"],
    summary="Social Auth Success",
    description="Handle successful social authentication and redirect to frontend",
    responses={302: BaseResponseSerializer}
)
class SocialAuthSuccessView(GenericAPIView, BaseAPIView, SocialAuthMixin):
    permission_classes = [AllowAny]  # Allow any since allauth handles session auth
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Generate JWT tokens after successful social authentication and redirect to frontend"""
        try:
            # Validate user authentication
            if not request.user.is_authenticated:
                return self.build_frontend_redirect(
                    status='error',
                    reason='User not authenticated',
                    provider='unknown'
                )
            
            user = request.user
            provider = self.get_user_provider(user)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            logger.info(f"Social auth success for user {user.id} via {provider}")
            
            # Redirect to frontend with tokens
            return self.build_frontend_redirect(
                status='success',
                token=access_token,
                refresh=refresh_token,
                provider=provider
            )
            
        except Exception as e:
            logger.error(f"Social auth success handler error: {str(e)}")
            return self.build_frontend_redirect(
                status='error',
                reason=str(e),
                provider='unknown'
            )


@social_router.register(r"auth/social/error", name="auth-social-error")
@extend_schema(
    tags=["Authentication"],
    summary="Social Auth Error",
    description="Handle social authentication errors and redirect to frontend",
    responses={302: BaseResponseSerializer}
)
class SocialAuthErrorView(GenericAPIView, BaseAPIView, SocialAuthMixin):
    permission_classes = [AllowAny]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Handle social authentication errors and redirect to frontend"""
        error = request.GET.get('error', 'unknown_error')
        error_description = request.GET.get('error_description', 'Social authentication failed')
        provider = request.GET.get('provider', 'unknown')
        
        logger.warning(f"Social auth error: {error} - {error_description}")
        
        # Redirect to frontend with error details
        return self.build_frontend_redirect(
            status='error',
            reason=error_description,
            provider=provider
        )