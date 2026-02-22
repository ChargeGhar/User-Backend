"""
Static content pages - unified endpoint for all content types
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call, cached_response
from api.common.serializers import BaseResponseSerializer
from api.user.content import serializers
from api.user.content.services import (
    ContentPageService
)

static_pages_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@static_pages_router.register("content", name="content-page")
@extend_schema(
    tags=["Content"],
    summary="Get Content Page",
    description="Retrieve content page by type (terms-of-service, privacy-policy, about, contact, renting-policy)",
    parameters=[
        OpenApiParameter(
            "page_type",
            OpenApiTypes.STR,
            description="Page type to retrieve",
            required=True,
            enum=["terms-of-service", "privacy-policy", "about", "contact", "renting-policy"]
        )
    ],
    responses={200: BaseResponseSerializer}
)
class ContentPagePublicView(GenericAPIView, BaseAPIView):
    """Unified content page endpoint"""
    serializer_class = serializers.ContentPagePublicSerializer
    permission_classes = [AllowAny]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get content page by type with caching"""
        def operation():
            page_type = request.query_params.get('page_type')

            if not page_type:
                from api.common.services.base import ServiceException
                raise ServiceException(
                    detail="page_type query parameter is required",
                    code="missing_parameter"
                )

            service = ContentPageService()
            page = service.get_page_by_type(page_type)
            serializer = self.get_serializer(page)
            return serializer.data

        return self.handle_service_operation(
            operation,
            success_message="Content page retrieved successfully",
            error_message="Failed to retrieve content page"
        )


