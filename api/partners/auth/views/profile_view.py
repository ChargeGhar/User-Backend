# api/partners/auth/views/profile_view.py
"""Partner Profile View."""

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
from api.partners.auth.services import PartnerAuthService
from api.partners.auth.serializers import PartnerProfileSerializer

profile_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@profile_router.register(r"me", name="partner-me")
@extend_schema(
    tags=["Partner Auth"],
    summary="Get Current Partner",
    description="Get current authenticated partner's profile.",
    responses={200: BaseResponseSerializer}
)
class PartnerMeView(GenericAPIView, BaseAPIView):
    """
    Get current partner profile.
    """
    serializer_class = PartnerProfileSerializer
    permission_classes = [IsAuthenticated, HasDashboardAccess]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        return self.handle_service_operation(
            lambda: PartnerAuthService().get_current_partner(user=request.user),
            success_message="Partner profile retrieved successfully"
        )
