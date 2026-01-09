"""
Admin points management views
============================================================

This module contains views for admin points management operations.

Created: 2025-11-11
"""
from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers
from api.admin.services import AdminPointsService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission
from api.user.points.serializers import PointsTransactionSerializer

points_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)


# ============================================================
# Points Management Views
# ============================================================

@points_admin_router.register(r"admin/points/adjust", name="admin-points-adjust")
@extend_schema(
    tags=["Admin - Points"],
    summary="Adjust User Points",
    description="Manually adjust user points (add or deduct) with reason (Staff only)",
    request=serializers.AdjustUserPointsSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminAdjustPointsView(GenericAPIView, BaseAPIView):
    """Admin adjust user points"""
    serializer_class = serializers.AdjustUserPointsSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        """Adjust user points"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminPointsService()
            result = service.adjust_user_points(
                user_id=str(serializer.validated_data['user_id']),
                points=serializer.validated_data['points'],
                adjustment_type=serializer.validated_data['adjustment_type'],
                reason=serializer.validated_data['reason'],
                admin_user=request.user
            )
            
            return result
        
        return self.handle_service_operation(
            operation,
            success_message="Points adjusted successfully",
            error_message="Failed to adjust points",
            operation_context="Admin points adjustment"
        )


@points_admin_router.register(r"admin/points/analytics", name="admin-points-analytics")
@extend_schema(
    tags=["Admin - Points"],
    summary="Points Analytics",
    description="Get comprehensive points analytics including totals, breakdowns, and top earners (Staff only)",
    parameters=[serializers.PointsAnalyticsFiltersSerializer],
    responses={200: BaseResponseSerializer}
)
class AdminPointsAnalyticsView(GenericAPIView, BaseAPIView):
    """Admin points analytics"""
    serializer_class = serializers.PointsAnalyticsFiltersSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get points analytics"""
        def operation():
            # Parse filters
            filter_serializer = serializers.PointsAnalyticsFiltersSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminPointsService()
            analytics = service.get_points_analytics(
                start_date=filter_serializer.validated_data.get('start_date'),
                end_date=filter_serializer.validated_data.get('end_date')
            )
            
            return analytics
        
        return self.handle_service_operation(
            operation,
            success_message="Points analytics retrieved successfully",
            error_message="Failed to retrieve points analytics",
            operation_context="Admin points analytics"
        )


@points_admin_router.register(r"admin/points/history", name="admin-points-history")
@extend_schema(
    tags=["Admin - Points"],
    summary="Points Transaction History",
    description="Get paginated points transaction history for all users with filters (Staff only). Use 'search' field to filter by user ID (numeric), username, email, or transaction description.",
    parameters=[serializers.PointsHistoryFiltersSerializer],
    responses={200: BaseResponseSerializer}
)
class AdminPointsHistoryView(GenericAPIView, BaseAPIView):
    """Admin points transaction history"""
    serializer_class = serializers.PointsHistoryFiltersSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get points transaction history"""
        def operation():
            # Parse filters
            filter_serializer = serializers.PointsHistoryFiltersSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            
            filters = {
                'transaction_type': filter_serializer.validated_data.get('transaction_type'),
                'source': filter_serializer.validated_data.get('source'),
                'search': filter_serializer.validated_data.get('search'),
                'start_date': filter_serializer.validated_data.get('start_date'),
                'end_date': filter_serializer.validated_data.get('end_date'),
                'page': filter_serializer.validated_data.get('page', 1),
                'page_size': filter_serializer.validated_data.get('page_size', 20)
            }
            
            service = AdminPointsService()
            paginated_result = service.get_all_points_history(filters)
            
            # Serialize the transactions
            transaction_serializer = PointsTransactionSerializer(
                paginated_result['results'], 
                many=True
            )
            paginated_result['results'] = transaction_serializer.data
            
            return paginated_result
        
        return self.handle_service_operation(
            operation,
            success_message="Points history retrieved successfully",
            error_message="Failed to retrieve points history",
            operation_context="Admin points history"
        )
