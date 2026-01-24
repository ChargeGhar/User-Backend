# api/partners/auth/views/password_views.py
"""Partner Password Management Views."""

from __future__ import annotations

import logging
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.permissions import HasDashboardAccess
from api.partners.auth.services import PartnerPasswordService
from api.partners.auth.serializers import ChangePasswordSerializer

password_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@password_router.register(r"change-password", name="partner-change-password")
@extend_schema(
    tags=["Partner Auth"],
    summary="Change Password",
    description="Change password for authenticated partner. Requires current password.",
    responses={200: BaseResponseSerializer}
)
class PartnerChangePasswordView(GenericAPIView, BaseAPIView):
    """
    Change password for authenticated partner.
    
    Requires current password for verification.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated, HasDashboardAccess]
    
    @log_api_call(include_request_data=True)
    def put(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.handle_service_operation(
            lambda: PartnerPasswordService().change_password(
                user=request.user,
                current_password=serializer.validated_data['current_password'],
                new_password=serializer.validated_data['new_password']
            ),
            success_message="Password changed successfully"
        )
