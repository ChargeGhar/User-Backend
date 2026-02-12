"""
Public app configuration endpoints.
"""
from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.user.system.serializers import PublicAppConfigResponseSerializer
from api.user.system.services import AppConfigService

app_config_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@app_config_router.register(r"app/config", name="app-config")
@extend_schema(
    tags=["App"],
    summary="Get Public App Configurations",
    description="Returns only configurations marked as public and active.",
    responses={200: PublicAppConfigResponseSerializer},
)
class AppConfigPublicView(GenericAPIView, BaseAPIView):
    """Return app configurations safe for client consumption."""

    permission_classes = [AllowAny]
    serializer_class = PublicAppConfigResponseSerializer

    @log_api_call()
    def get(self, request: Request) -> Response:
        def operation():
            service = AppConfigService()
            configs = service.get_public_configs()
            serializer = self.get_serializer(
                {
                    "configs": configs,
                    "total_count": len(configs),
                }
            )
            return serializer.data

        return self.handle_service_operation(
            operation,
            success_message="Public app configurations retrieved successfully",
            error_message="Failed to retrieve public app configurations",
        )
