# api/partners/auth/views/token_views.py
"""Partner Token Management Views."""

from __future__ import annotations

import logging
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import rate_limit, log_api_call
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.services import PartnerAuthService
from api.partners.auth.serializers import RefreshTokenSerializer, LogoutSerializer

token_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@token_router.register(r"refresh", name="partner-refresh")
@extend_schema(
    tags=["Partner Auth"],
    summary="Refresh Token",
    description="Get new access token using refresh token. Validates partner is still active.",
    responses={200: BaseResponseSerializer}
)
class PartnerRefreshTokenView(GenericAPIView, BaseAPIView):
    """
    Refresh JWT tokens.
    
    Validates partner is still active before issuing new tokens.
    Old refresh token is blacklisted.
    """
    serializer_class = RefreshTokenSerializer
    permission_classes = [AllowAny]
    
    @rate_limit(max_requests=10, window_seconds=300)
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: PartnerAuthService().refresh_token(
                refresh_token=serializer.validated_data['refresh_token']
            ),
            success_message="Token refreshed successfully"
        )


@token_router.register(r"logout", name="partner-logout")
@extend_schema(
    tags=["Partner Auth"],
    summary="Logout",
    description="Logout and blacklist refresh token.",
    responses={200: BaseResponseSerializer}
)
class PartnerLogoutView(GenericAPIView, BaseAPIView):
    """
    Logout and blacklist refresh token.
    """
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: PartnerAuthService().logout(
                refresh_token=serializer.validated_data['refresh_token']
            ),
            success_message="Logged out successfully"
        )
