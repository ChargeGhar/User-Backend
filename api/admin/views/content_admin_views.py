"""
Content administration - manage pages, FAQs, contact info, and banners
========================================================================

Migrated from api/content/views/admin_views.py
Renamed to content_admin_views.py for clarity and consistency
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin.services import AdminContentService
from api.common.decorators import log_api_call, cached_response
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.content import serializers
from api.user.auth.permissions import IsStaffPermission

content_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)


# ==================== Content Pages ====================

@content_admin_router.register(r"admin/content/pages", name="admin-content-pages")
@extend_schema(
    tags=["Admin - Contents"],
    summary="Admin Content Pages",
    description="Manage content pages (admin only)",
    request=serializers.ContentPageSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminContentPagesView(GenericAPIView, BaseAPIView):
    """Admin content pages management"""
    serializer_class = serializers.ContentPageSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call(include_request_data=True)
    def put(self, request: Request) -> Response:
        """Update content page"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminContentService()
            page = service.update_content_page(
                page_type=serializer.validated_data['page_type'],
                title=serializer.validated_data['title'],
                content=serializer.validated_data['content'],
                admin_user=request.user
            )
            
            return self.get_serializer(page).data
        
        return self.handle_service_operation(
            operation,
            "Content page updated successfully",
            "Failed to update content page"
        )


@content_admin_router.register(r"admin/content/analytics", name="admin-content-analytics")
@extend_schema(
    tags=["Admin - Contents"],
    summary="Content Analytics",
    description="Get comprehensive content analytics (admin only)",
    responses={200: BaseResponseSerializer}
)
class AdminContentAnalyticsView(GenericAPIView, BaseAPIView):
    """Admin content analytics"""
    serializer_class = serializers.ContentAnalyticsSerializer
    permission_classes = [IsStaffPermission]

    @cached_response(timeout=1800)
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get content analytics"""
        def operation():
            service = AdminContentService()
            analytics = service.get_content_analytics()
            return self.get_serializer(analytics).data
        
        return self.handle_service_operation(
            operation,
            "Content analytics retrieved successfully",
            "Failed to retrieve content analytics"
        )


# ==================== FAQs ====================

@content_admin_router.register(r"admin/content/faqs", name="admin-content-faqs")
@extend_schema(
    tags=["Admin - Contents"],
    summary="Admin FAQ Management",
    description="List and create FAQs (admin only)",
    request=serializers.FAQSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminFAQView(GenericAPIView, BaseAPIView):
    """Admin FAQ management"""
    serializer_class = serializers.FAQSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """List all FAQs"""
        def operation():
            service = AdminContentService()
            faqs = service.get_all_faqs()
            return self.get_serializer(faqs, many=True).data
        
        return self.handle_service_operation(
            operation,
            "FAQs retrieved successfully",
            "Failed to retrieve FAQs"
        )

    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        """Create new FAQ"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminContentService()
            faq = service.create_faq(
                question=serializer.validated_data['question'],
                answer=serializer.validated_data['answer'],
                category=serializer.validated_data['category'],
                admin_user=request.user
            )
            
            return self.get_serializer(faq).data
        
        return self.handle_service_operation(
            operation,
            "FAQ created successfully",
            "Failed to create FAQ"
        )


@content_admin_router.register(r"admin/content/faqs/<str:faq_id>", name="admin-content-faq-detail")
class AdminFAQDetailView(GenericAPIView, BaseAPIView):
    """Admin FAQ detail management"""
    serializer_class = serializers.FAQSerializer
    permission_classes = [IsStaffPermission]

    @extend_schema(
        operation_id="admin_content_faq_detail_retrieve",
        tags=["Admin - Contents"],
        summary="Get FAQ by ID",
        description="Retrieve specific FAQ details (admin only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request, faq_id: str) -> Response:
        """Get FAQ by ID"""
        def operation():
            service = AdminContentService()
            faq = service.get_faq_by_id(faq_id)
            return self.get_serializer(faq).data
        
        return self.handle_service_operation(
            operation,
            "FAQ retrieved successfully",
            "Failed to retrieve FAQ"
        )

    @extend_schema(
        operation_id="admin_content_faq_detail_update",
        tags=["Admin - Contents"],
        summary="Update FAQ",
        description="Update specific FAQ (admin only)",
        request=serializers.FAQSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call(include_request_data=True)
    def put(self, request: Request, faq_id: str) -> Response:
        """Update FAQ"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminContentService()
            faq = service.update_faq(
                faq_id=faq_id,
                question=serializer.validated_data['question'],
                answer=serializer.validated_data['answer'],
                category=serializer.validated_data['category'],
                admin_user=request.user
            )
            
            return self.get_serializer(faq).data
        
        return self.handle_service_operation(
            operation,
            "FAQ updated successfully",
            "Failed to update FAQ"
        )

    @extend_schema(
        operation_id="admin_content_faq_detail_delete",
        tags=["Admin - Contents"],
        summary="Delete FAQ",
        description="Delete specific FAQ (admin only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call(include_request_data=True)
    def delete(self, request: Request, faq_id: str) -> Response:
        """Delete FAQ"""
        def operation():
            service = AdminContentService()
            service.delete_faq(faq_id, request.user)
            return {"deleted": True}
        
        return self.handle_service_operation(
            operation,
            "FAQ deleted successfully",
            "Failed to delete FAQ"
        )


# ==================== Contact Info ====================

@content_admin_router.register(r"admin/content/contact", name="admin-content-contact")
@extend_schema(
    tags=["Admin - Contents"],
    summary="Admin Contact Info Management",
    description="List and create/update contact information (admin only)",
    request=serializers.ContactInfoSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminContactInfoView(GenericAPIView, BaseAPIView):
    """Admin contact info management"""
    serializer_class = serializers.ContactInfoSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """List all contact info"""
        def operation():
            service = AdminContentService()
            contact_info = service.get_all_contact_info()
            return self.get_serializer(contact_info, many=True).data
        
        return self.handle_service_operation(
            operation,
            "Contact info retrieved successfully",
            "Failed to retrieve contact info"
        )

    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        """Create/Update contact info"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminContentService()
            contact_info = service.update_contact_info(
                info_type=serializer.validated_data['info_type'],
                label=serializer.validated_data['label'],
                value=serializer.validated_data['value'],
                description=serializer.validated_data.get('description', ''),
                admin_user=request.user
            )
            
            return self.get_serializer(contact_info).data
        
        return self.handle_service_operation(
            operation,
            "Contact info updated successfully",
            "Failed to update contact info"
        )


@content_admin_router.register(r"admin/content/contact/<str:contact_id>", name="admin-content-contact-detail")
class AdminContactInfoDetailView(GenericAPIView, BaseAPIView):
    """Admin contact info detail management"""
    serializer_class = serializers.ContactInfoSerializer
    permission_classes = [IsStaffPermission]

    @extend_schema(
        operation_id="admin_content_contact_detail_retrieve",
        tags=["Admin - Contents"],
        summary="Get Contact Info by ID",
        description="Retrieve specific contact info details (admin only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request, contact_id: str) -> Response:
        """Get contact info by ID"""
        def operation():
            service = AdminContentService()
            contact_info = service.get_contact_info_by_id(contact_id)
            return self.get_serializer(contact_info).data
        
        return self.handle_service_operation(
            operation,
            "Contact info retrieved successfully",
            "Failed to retrieve contact info"
        )

    @extend_schema(
        operation_id="admin_content_contact_detail_delete",
        tags=["Admin - Contents"],
        summary="Delete Contact Info",
        description="Delete specific contact info (admin only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call(include_request_data=True)
    def delete(self, request: Request, contact_id: str) -> Response:
        """Delete contact info"""
        def operation():
            service = AdminContentService()
            service.delete_contact_info(contact_id, request.user)
            return {"deleted": True}
        
        return self.handle_service_operation(
            operation,
            "Contact info deleted successfully",
            "Failed to delete contact info"
        )


# ==================== Banners ====================

@content_admin_router.register(r"admin/content/banners", name="admin-content-banners")
@extend_schema(
    tags=["Admin - Contents"],
    summary="Admin Banner Management",
    description="List and create banners (admin only)",
    request=serializers.BannerSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminBannerView(GenericAPIView, BaseAPIView):
    """Admin banner management"""
    serializer_class = serializers.BannerSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """List all banners"""
        def operation():
            service = AdminContentService()
            banners = service.get_all_banners()
            return self.get_serializer(banners, many=True).data
        
        return self.handle_service_operation(
            operation,
            "Banners retrieved successfully",
            "Failed to retrieve banners"
        )

    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        """Create new banner"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminContentService()
            banner = service.create_banner(
                title=serializer.validated_data['title'],
                description=serializer.validated_data.get('description', ''),
                image_url=serializer.validated_data['image_url'],
                redirect_url=serializer.validated_data.get('redirect_url', ''),
                valid_from=serializer.validated_data['valid_from'],
                valid_until=serializer.validated_data['valid_until'],
                admin_user=request.user
            )
            
            return self.get_serializer(banner).data
        
        return self.handle_service_operation(
            operation,
            "Banner created successfully",
            "Failed to create banner"
        )


@content_admin_router.register(r"admin/content/banners/<str:banner_id>", name="admin-content-banner-detail")
class AdminBannerDetailView(GenericAPIView, BaseAPIView):
    """Admin banner detail management"""
    serializer_class = serializers.BannerSerializer
    permission_classes = [IsStaffPermission]

    @extend_schema(
        operation_id="admin_content_banner_detail_retrieve",
        tags=["Admin - Contents"],
        summary="Get Banner by ID",
        description="Retrieve specific banner details (admin only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request, banner_id: str) -> Response:
        """Get banner by ID"""
        def operation():
            service = AdminContentService()
            banner = service.get_banner_by_id(banner_id)
            return self.get_serializer(banner).data
        
        return self.handle_service_operation(
            operation,
            "Banner retrieved successfully",
            "Failed to retrieve banner"
        )

    @extend_schema(
        operation_id="admin_content_banner_detail_update",
        tags=["Admin - Contents"],
        summary="Update Banner",
        description="Update specific banner (admin only)",
        request=serializers.BannerSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call(include_request_data=True)
    def put(self, request: Request, banner_id: str) -> Response:
        """Update banner"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminContentService()
            banner = service.update_banner(
                banner_id=banner_id,
                title=serializer.validated_data['title'],
                description=serializer.validated_data.get('description', ''),
                image_url=serializer.validated_data['image_url'],
                redirect_url=serializer.validated_data.get('redirect_url', ''),
                valid_from=serializer.validated_data['valid_from'],
                valid_until=serializer.validated_data['valid_until'],
                admin_user=request.user
            )
            
            return self.get_serializer(banner).data
        
        return self.handle_service_operation(
            operation,
            "Banner updated successfully",
            "Failed to update banner"
        )

    @extend_schema(
        operation_id="admin_content_banner_detail_delete",
        tags=["Admin - Contents"],
        summary="Delete Banner",
        description="Delete specific banner (admin only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call(include_request_data=True)
    def delete(self, request: Request, banner_id: str) -> Response:
        """Delete banner"""
        def operation():
            service = AdminContentService()
            service.delete_banner(banner_id, request.user)
            return {"deleted": True}
        
        return self.handle_service_operation(
            operation,
            "Banner deleted successfully",
            "Failed to delete banner"
        )
