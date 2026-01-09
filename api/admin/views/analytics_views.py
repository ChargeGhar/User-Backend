"""
Admin Analytics Views
============================================================

This module contains views for analytics endpoints including:
- Rentals over time (charts)
- Revenue over time (charts)

Created: 2025-11-07
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin.serializers import (
    RentalsOverTimeQuerySerializer,
    RentalsOverTimeResponseSerializer,
    RevenueOverTimeQuerySerializer,
    RevenueOverTimeResponseSerializer
)
from api.admin.services import AdminAnalyticsService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission

analytics_router = CustomViewRouter()


@analytics_router.register(r"admin/analytics/rentals-over-time", name="admin-rentals-over-time")
class RentalsOverTimeView(GenericAPIView, BaseAPIView):
    """Analytics endpoint for rentals over time with chart data"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=["Admin - Analytics"],
        summary="Rentals Over Time Analytics",
        description="""
        Get rental statistics over time for chart visualization.
        
        **Features**:
        - Aggregate by daily, weekly, or monthly periods
        - Filter by rental status
        - Get breakdown by status (completed, active, pending, cancelled, overdue)
        - Summary statistics (average, peak period)
        - Ready-to-use chart data format
        
        **Use Cases**:
        - Dashboard charts showing rental trends
        - Performance monitoring
        - Business analytics
        """,
        parameters=[
            OpenApiParameter(
                name="period",
                type=OpenApiTypes.STR,
                required=True,
                enum=['daily', 'weekly', 'monthly'],
                description="Aggregation period for data grouping"
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                required=False,
                description="Start date (YYYY-MM-DD). Default: 30 days ago"
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                required=False,
                description="End date (YYYY-MM-DD). Default: today"
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                required=False,
                enum=['PENDING', 'ACTIVE', 'COMPLETED', 'CANCELLED', 'OVERDUE'],
                description="Filter by specific rental status"
            ),
        ],
        responses={
            200: RentalsOverTimeResponseSerializer,
            400: BaseResponseSerializer
        }
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get rentals over time analytics"""
        def operation():
            # Validate query parameters
            query_serializer = RentalsOverTimeQuerySerializer(data=request.query_params)
            query_serializer.is_valid(raise_exception=True)
            
            # Get analytics data
            service = AdminAnalyticsService()
            data = service.get_rentals_over_time(
                period=query_serializer.validated_data['period'],
                start_date=query_serializer.validated_data.get('start_date'),
                end_date=query_serializer.validated_data.get('end_date'),
                status=query_serializer.validated_data.get('status')
            )
            
            return data
        
        return self.handle_service_operation(
            operation,
            success_message="Rentals analytics retrieved successfully",
            error_message="Failed to retrieve rentals analytics"
        )


@analytics_router.register(r"admin/analytics/revenue-over-time", name="admin-revenue-over-time")
class RevenueOverTimeView(GenericAPIView, BaseAPIView):
    """Analytics endpoint for revenue over time with chart data"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=["Admin - Analytics"],
        summary="Revenue Over Time Analytics",
        description="""
        Get revenue statistics over time for chart visualization.
        
        **Features**:
        - Aggregate by daily, weekly, or monthly periods
        - Filter by transaction type
        - Get breakdown by revenue source (rentals, top-ups, fines)
        - Summary statistics (average, peak period, growth rate)
        - Ready-to-use chart data format
        
        **Revenue Sources**:
        - Rental revenue (base rental charges)
        - Rental due revenue (overdue payments)
        - Top-up revenue (wallet recharges)
        - Fine revenue (penalties)
        
        **Use Cases**:
        - Financial dashboard charts
        - Revenue trend analysis
        - Business performance monitoring
        """,
        parameters=[
            OpenApiParameter(
                name="period",
                type=OpenApiTypes.STR,
                required=True,
                enum=['daily', 'weekly', 'monthly'],
                description="Aggregation period for data grouping"
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                required=False,
                description="Start date (YYYY-MM-DD). Default: 180 days ago"
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                required=False,
                description="End date (YYYY-MM-DD). Default: today"
            ),
            OpenApiParameter(
                name="transaction_type",
                type=OpenApiTypes.STR,
                required=False,
                enum=['TOPUP', 'RENTAL', 'RENTAL_DUE', 'REFUND', 'FINE'],
                description="Filter by specific transaction type"
            ),
        ],
        responses={
            200: RevenueOverTimeResponseSerializer,
            400: BaseResponseSerializer
        }
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get revenue over time analytics"""
        def operation():
            # Validate query parameters
            query_serializer = RevenueOverTimeQuerySerializer(data=request.query_params)
            query_serializer.is_valid(raise_exception=True)
            
            # Get analytics data
            service = AdminAnalyticsService()
            data = service.get_revenue_over_time(
                period=query_serializer.validated_data['period'],
                start_date=query_serializer.validated_data.get('start_date'),
                end_date=query_serializer.validated_data.get('end_date'),
                transaction_type=query_serializer.validated_data.get('transaction_type')
            )
            
            return data
        
        return self.handle_service_operation(
            operation,
            success_message="Revenue analytics retrieved successfully",
            error_message="Failed to retrieve revenue analytics"
        )
