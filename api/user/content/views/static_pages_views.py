"""
Static content pages - terms, privacy policy, and about
"""
import logging

from drf_spectacular.utils import extend_schema
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

@static_pages_router.register("content/terms-of-service", name="content-terms")
@extend_schema(
    tags=["Content"],
    summary="Terms of Service",
    description="Retrieve current terms of service content",
    responses={200: BaseResponseSerializer}
)
class TermsOfServiceView(GenericAPIView, BaseAPIView):
    """Terms of service endpoint"""
    serializer_class = serializers.ContentPagePublicSerializer
    permission_classes = [AllowAny]

    @cached_response(timeout=3600)  # 1 hour cache for static content
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get terms of service with caching"""
        def operation():
            service = ContentPageService()
            page = service.get_page_by_type('terms-of-service')
            serializer = self.get_serializer(page)
            return serializer.data

        return self.handle_service_operation(
            operation,
            success_message="Terms of service retrieved successfully",
            error_message="Failed to retrieve terms of service"
        )

@static_pages_router.register("content/privacy-policy", name="content-privacy")
@extend_schema(
    tags=["Content"],
    summary="Privacy Policy",
    description="Retrieve current privacy policy content (cached for performance)",
    responses={200: BaseResponseSerializer}
)
class PrivacyPolicyView(GenericAPIView, BaseAPIView):
    """Privacy policy endpoint with caching"""
    serializer_class = serializers.ContentPagePublicSerializer
    permission_classes = [AllowAny]

    @cached_response(timeout=3600)  # 1 hour cache for static content
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get privacy policy with caching"""
        def operation():
            service = ContentPageService()
            page = service.get_page_by_type('privacy-policy')
            serializer = self.get_serializer(page)
            return serializer.data

        return self.handle_service_operation(
            operation,
            success_message="Privacy policy retrieved successfully",
            error_message="Failed to retrieve privacy policy"
        )

@static_pages_router.register("content/about", name="content-about")
@extend_schema(
    tags=["Content"],
    summary="About Us",
    description="Retrieve about us information (cached for performance)",
    responses={200: BaseResponseSerializer}
)
class AboutView(GenericAPIView, BaseAPIView):
    """About us endpoint with caching"""
    serializer_class = serializers.ContentPagePublicSerializer
    permission_classes = [AllowAny]

    @cached_response(timeout=3600)  # 1 hour cache for static content
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get about information with caching"""
        def operation():
            service = ContentPageService()
            page = service.get_page_by_type('about')
            serializer = self.get_serializer(page)
            return serializer.data

        return self.handle_service_operation(
            operation,
            success_message="About information retrieved successfully",
            error_message="Failed to retrieve about information"
        )

