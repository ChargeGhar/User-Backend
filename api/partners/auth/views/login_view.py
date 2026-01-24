# api/partners/auth/views/login_view.py
"""Partner Login View."""

from __future__ import annotations

import logging
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import rate_limit, log_api_call
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.services import PartnerAuthService
from api.partners.auth.serializers import PartnerLoginSerializer

login_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@login_router.register(r"login", name="partner-login")
@extend_schema(
    tags=["Partner Auth"],
    summary="Partner Login",
    description="Authenticate partner with email and password. Returns JWT tokens. Non-Revenue vendors will be rejected.",
    responses={200: BaseResponseSerializer}
)
class PartnerLoginView(GenericAPIView, BaseAPIView):
    """
    Partner login endpoint.
    
    Authenticates partner with email and password.
    Returns JWT tokens and partner profile.
    """
    serializer_class = PartnerLoginSerializer
    permission_classes = [AllowAny]
    
    @rate_limit(max_requests=5, window_seconds=300)
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: PartnerAuthService().login(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password']
            ),
            success_message="Login successful"
        )
