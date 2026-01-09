"""
Admin Rental Views - Rental management and issue operations
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers
from api.admin.services import AdminRentalService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer, PaginatedResponseSerializer
from api.user.auth.permissions import IsStaffPermission

rental_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@rental_router.register(r"admin/rentals", name="admin-rentals")
@extend_schema(
    tags=["Admin - Rentals"],
    summary="List Rentals",
    description="Get list of all rentals with filtering and pagination (Staff only)",
    parameters=[
        OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status (PENDING, ACTIVE, COMPLETED, CANCELLED, OVERDUE)"),
        OpenApiParameter("payment_status", OpenApiTypes.STR, description="Filter by payment status (PENDING, PAID, FAILED, REFUNDED)"),
        OpenApiParameter("user_id", OpenApiTypes.INT, description="Filter by user ID"),
        OpenApiParameter("station_id", OpenApiTypes.STR, description="Filter by station ID"),
        OpenApiParameter("search", OpenApiTypes.STR, description="Search by rental code or user name/phone"),
        OpenApiParameter("recent", OpenApiTypes.STR, description="Recent rentals: 'today', '24h', '7d', '30d'"),
        OpenApiParameter("start_date", OpenApiTypes.DATETIME, description="Filter rentals started after this date"),
        OpenApiParameter("end_date", OpenApiTypes.DATETIME, description="Filter rentals started before this date"),
        OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
        OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page"),
    ],
    responses={200: PaginatedResponseSerializer}
)
class AdminRentalsListView(GenericAPIView, BaseAPIView):
    """Admin rentals list with comprehensive filtering"""
    serializer_class = serializers.AdminRentalSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get list of rentals with optional filtering"""
        def operation():
            # Parse filters
            filters = {
                'status': request.query_params.get('status'),
                'payment_status': request.query_params.get('payment_status'),
                'user_id': request.query_params.get('user_id'),
                'station_id': request.query_params.get('station_id'),
                'search': request.query_params.get('search'),
                'recent': request.query_params.get('recent'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': int(request.query_params.get('page', 1)),
                'page_size': int(request.query_params.get('page_size', 20)),
            }
            
            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}
            
            # Get rentals
            service = AdminRentalService()
            rentals_data = service.get_rentals_list(filters)
            
            # Serialize rentals
            serializer = serializers.AdminRentalSerializer(
                rentals_data['results'], many=True
            )
            
            return {
                'results': serializer.data,
                'pagination': rentals_data['pagination']
            }
        
        return self.handle_service_operation(
            operation,
            "Rentals retrieved successfully",
            "Failed to retrieve rentals"
        )


# IMPORTANT: Specific routes must come before generic ones
# /admin/rentals/issues must come before /admin/rentals/<rental_id>

@rental_router.register(r"admin/rentals/issues", name="admin-rental-issues")
@extend_schema(
    tags=["Admin - Rentals"],
    summary="List Rental Issues",
    description="Get list of all rental issues reported by users with filtering (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminRentalIssuesView(GenericAPIView, BaseAPIView):
    """Admin rental issues list and management"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get list of rental issues with optional filtering"""
        def operation():
            # Get query parameters
            status_filter = request.query_params.get('status')
            issue_type = request.query_params.get('issue_type')
            search = request.query_params.get('search')
            ordering = request.query_params.get('ordering', '-reported_at')
            
            # Get issues
            service = AdminRentalService()
            issues = service.get_rental_issues(
                status=status_filter,
                issue_type=issue_type,
                search=search,
                ordering=ordering
            )
            
            # Paginate
            page = self.paginate_queryset(issues)
            if page is not None:
                serializer = serializers.AdminRentalIssueSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = serializers.AdminRentalIssueSerializer(issues, many=True)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Rental issues retrieved successfully",
            "Failed to retrieve rental issues"
        )


@rental_router.register(r"admin/rentals/issues/<str:issue_id>", name="admin-rental-issue-detail")
@extend_schema(
    tags=["Admin - Rentals"],
    summary="Rental Issue Detail",
    description="Get, update or delete a specific rental issue (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminRentalIssueDetailView(GenericAPIView, BaseAPIView):
    """Admin rental issue detail, update, and delete"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request, issue_id: str) -> Response:
        """Get specific rental issue details"""
        def operation():
            service = AdminRentalService()
            issue = service.get_rental_issue(issue_id)
            serializer = serializers.AdminRentalIssueDetailSerializer(issue)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Rental issue retrieved successfully",
            "Failed to retrieve rental issue"
        )

    @extend_schema(
        request=serializers.UpdateRentalIssueSerializer
    )
    @log_api_call(include_request_data=True)
    def patch(self, request: Request, issue_id: str) -> Response:
        """Update rental issue status"""
        def operation():
            serializer = serializers.UpdateRentalIssueSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminRentalService()
            issue = service.update_rental_issue_status(
                issue_id=issue_id,
                status=serializer.validated_data['status'],
                admin_user=request.user,
                notes=serializer.validated_data.get('notes'),
                request=request
            )
            
            result_serializer = serializers.AdminRentalIssueDetailSerializer(issue)
            return result_serializer.data
        
        return self.handle_service_operation(
            operation,
            "Rental issue status updated successfully",
            "Failed to update rental issue status"
        )

    @log_api_call()
    def delete(self, request: Request, issue_id: str) -> Response:
        """Delete rental issue (soft delete)"""
        def operation():
            service = AdminRentalService()
            return service.delete_rental_issue(
                issue_id=issue_id,
                admin_user=request.user,
                request=request
            )
        
        return self.handle_service_operation(
            operation,
            "Rental issue deleted successfully",
            "Failed to delete rental issue"
        )


# Generic route with <rental_id> parameter - MUST come after specific routes
@rental_router.register(r"admin/rentals/<str:rental_id>", name="admin-rental-detail")
@extend_schema(
    tags=["Admin - Rentals"],
    summary="Rental Detail",
    description="Get detailed information about a specific rental (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminRentalDetailView(GenericAPIView, BaseAPIView):
    """Admin rental detail view"""
    serializer_class = serializers.AdminRentalDetailSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request, rental_id: str) -> Response:
        """Get specific rental details"""
        def operation():
            service = AdminRentalService()
            rental = service.get_rental_detail(rental_id)
            serializer = serializers.AdminRentalDetailSerializer(rental)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Rental details retrieved successfully",
            "Failed to retrieve rental details"
        )
