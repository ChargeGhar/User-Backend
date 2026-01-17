"""
Admin Advertisement Views
========================
Views for admin ad operations: list, detail, review, actions, schedule
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.generics import GenericAPIView
from api.user.auth.permissions import IsStaffPermission
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.advertisements import serializers
from api.admin.services.admin_ad_service import AdminAdService

admin_ads_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@admin_ads_router.register(r"ads/requests", name="admin-ad-list")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="List Ad Requests",
    description="Get list of all advertisement requests with filters"
)
class AdminAdRequestListView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdminAdRequestListSerializer
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        summary="List All Ad Requests",
        description="Returns paginated list of all ad requests with optional filters",
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by status',
                required=False
            ),
            OpenApiParameter(
                name='user_id',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by user ID',
                required=False
            ),
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Search in title, full_name, user email',
                required=False
            )
        ],
        responses={
            200: serializers.AdminAdRequestListSerializer(many=True)
        }
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """List all ad requests"""
        def operation():
            service = AdminAdService()
            
            # Get filters from query params
            filters = {}
            if request.query_params.get('status'):
                filters['status'] = request.query_params.get('status')
            if request.query_params.get('user_id'):
                filters['user_id'] = request.query_params.get('user_id')
            if request.query_params.get('search'):
                filters['search'] = request.query_params.get('search')
            
            ad_requests = service.get_ad_requests(filters=filters)
            
            serializer = self.get_serializer(ad_requests, many=True)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad requests retrieved successfully",
            error_message="Failed to retrieve ad requests"
        )


@admin_ads_router.register(r"ads/requests/<str:ad_id>", name="admin-ad-detail")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="Get Ad Request Details",
    description="Get detailed information about a specific ad request"
)
class AdminAdRequestDetailView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdminAdRequestDetailSerializer
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        summary="Get Ad Request Detail",
        description="Returns complete details of ad request including content, stations, and transaction",
        responses={
            200: serializers.AdminAdRequestDetailSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def get(self, request: Request, ad_id: str) -> Response:
        """Get ad request details"""
        def operation():
            service = AdminAdService()
            ad_request = service.get_ad_request_detail(ad_id)
            
            serializer = self.get_serializer(ad_request)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad request details retrieved successfully",
            error_message="Failed to retrieve ad request details"
        )


@admin_ads_router.register(r"ads/requests/<str:ad_id>/review", name="admin-ad-review")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="Review Ad Request",
    description="Review ad request and set pricing, stations, and schedule"
)
class AdminAdReviewView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdminAdReviewSerializer
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        summary="Review and Configure Ad",
        description="Review ad request and configure: title, description, pricing, "
                    "duration, stations, and content settings. "
                    "Valid for SUBMITTED or UNDER_REVIEW status.",
        request=serializers.AdminAdReviewSerializer,
        responses={
            200: serializers.AdminAdRequestDetailSerializer,
            400: BaseResponseSerializer
        }
    )
    @log_api_call(include_request_data=True)
    def patch(self, request: Request, ad_id: str) -> Response:
        """Review ad request"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminAdService()
            ad_request = service.review_ad_request(
                ad_id=ad_id,
                admin_user=request.user,
                validated_data=serializer.validated_data
            )
            
            response_serializer = serializers.AdminAdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad request reviewed successfully",
            error_message="Failed to review ad request"
        )


@admin_ads_router.register(r"ads/requests/<str:ad_id>/action", name="admin-ad-action")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="Perform Ad Action",
    description="Perform actions: approve, reject, schedule, pause, resume, cancel, complete"
)
class AdminAdActionView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdminAdActionSerializer
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        summary="Execute Ad Action",
        description="""
        Perform various actions on ad request:
        
        **APPROVE**: Approve reviewed ad (UNDER_REVIEW → PENDING_PAYMENT)
        
        **REJECT**: Reject ad with reason (SUBMITTED/UNDER_REVIEW → REJECTED)
        - Requires: rejection_reason
        
        **SCHEDULE**: Schedule paid ad (PAID → SCHEDULED)
        - Requires: start_date
        - Optional: end_date (auto-calculated if not provided)
        
        **PAUSE**: Pause running ad (RUNNING → PAUSED)
        
        **RESUME**: Resume paused ad (PAUSED → RUNNING)
        
        **CANCEL**: Cancel ad (Any except COMPLETED → CANCELLED)
        - Optional: reason
        
        **COMPLETE**: Mark ad as completed (RUNNING → COMPLETED)
        """,
        request=serializers.AdminAdActionSerializer,
        responses={
            200: serializers.AdminAdRequestDetailSerializer,
            400: BaseResponseSerializer
        }
    )
    @log_api_call(include_request_data=True)
    def post(self, request: Request, ad_id: str) -> Response:
        """Perform ad action"""
        action_name = request.data.get('action', 'unknown')
        
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminAdService()
            ad_request = service.perform_ad_action(
                ad_id=ad_id,
                admin_user=request.user,
                action=serializer.validated_data['action'],
                data=serializer.validated_data
            )
            
            response_serializer = serializers.AdminAdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message=f"Action '{action_name}' executed successfully",
            error_message="Failed to execute action"
        )


@admin_ads_router.register(r"ads/requests/<str:ad_id>/update-schedule", name="admin-ad-schedule-update")
@extend_schema(
    tags=["Admin - Advertisements"],
    summary="Update Ad Schedule",
    description="Update start/end dates for scheduled or running ads"
)
class AdminAdScheduleUpdateView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdminAdScheduleUpdateSerializer
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        summary="Update Ad Schedule Dates",
        description="Update start_date and/or end_date for ads in SCHEDULED, RUNNING, or PAUSED status. "
                    "At least one date must be provided.",
        request=serializers.AdminAdScheduleUpdateSerializer,
        responses={
            200: serializers.AdminAdRequestDetailSerializer,
            400: BaseResponseSerializer
        }
    )
    @log_api_call(include_request_data=True)
    def patch(self, request: Request, ad_id: str) -> Response:
        """Update ad schedule"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminAdService()
            ad_request = service.update_schedule(
                ad_id=ad_id,
                validated_data=serializer.validated_data
            )
            
            response_serializer = serializers.AdminAdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad schedule updated successfully",
            error_message="Failed to update ad schedule"
        )
