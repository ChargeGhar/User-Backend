"""
Admin referral and leaderboard management views
============================================================

This module contains views for admin referral and leaderboard operations.

Created: 2025-11-11
"""
from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status, serializers as drf_serializers
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers as admin_serializers
from api.admin.services import AdminReferralService, AdminLeaderboardService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission
from api.user.points.serializers import ReferralSerializer
from api.user.social.serializers import UserLeaderboardSerializer

referral_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)


# ============================================================
# Referral Management Views
# ============================================================

@referral_admin_router.register(
    r"admin/referrals/analytics", 
    name="admin-referral-analytics"
)
@extend_schema(
    tags=["Admin - Referrals"],
    summary="Referral Analytics",
    description="Get comprehensive referral analytics including conversion rates and top referrers (Staff only)",
    parameters=[admin_serializers.ReferralAnalyticsFiltersSerializer],
    responses={200: BaseResponseSerializer}
)
class AdminReferralAnalyticsView(GenericAPIView, BaseAPIView):
    """Admin referral analytics"""
    serializer_class = admin_serializers.ReferralAnalyticsFiltersSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get referral analytics"""
        def operation():
            # Parse filters
            filter_serializer = admin_serializers.ReferralAnalyticsFiltersSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminReferralService()
            analytics = service.get_referral_analytics(
                start_date=filter_serializer.validated_data.get('start_date'),
                end_date=filter_serializer.validated_data.get('end_date')
            )
            
            return analytics
        
        return self.handle_service_operation(
            operation,
            success_message="Referral analytics retrieved successfully",
            error_message="Failed to retrieve referral analytics",
            operation_context="Admin referral analytics"
        )


@referral_admin_router.register(
    r"admin/users/{user_id}/referrals", 
    name="admin-user-referrals"
)
@extend_schema(
    tags=["Admin - Referrals"],
    summary="User Referrals",
    description="Get paginated referrals for a specific user (Staff only)",
    parameters=[admin_serializers.UserReferralsFiltersSerializer],
    responses={200: BaseResponseSerializer}
)
class AdminUserReferralsView(GenericAPIView, BaseAPIView):
    """Admin user referrals"""
    serializer_class = admin_serializers.UserReferralsFiltersSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request, user_id: str) -> Response:
        """Get user referrals"""
        def operation():
            # Parse filters
            filter_serializer = admin_serializers.UserReferralsFiltersSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminReferralService()
            paginated_result = service.get_user_referrals(
                user_id=user_id,
                page=filter_serializer.validated_data.get('page', 1),
                page_size=filter_serializer.validated_data.get('page_size', 20)
            )
            
            # Serialize the referrals
            referral_serializer = ReferralSerializer(
                paginated_result['results'],
                many=True
            )
            paginated_result['results'] = referral_serializer.data
            
            return paginated_result
        
        return self.handle_service_operation(
            operation,
            success_message="User referrals retrieved successfully",
            error_message="Failed to retrieve user referrals",
            operation_context="Admin user referrals"
        )


@referral_admin_router.register(
    r"admin/referrals/<str:referral_id>/complete", 
    name="admin-referral-complete"
)
@extend_schema(
    tags=["Admin - Referrals"],
    summary="Complete Referral",
    description="Manually complete a referral (admin override) (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminCompleteReferralView(GenericAPIView, BaseAPIView):
    """Admin complete referral"""
    serializer_class = drf_serializers.Serializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def post(self, request: Request, referral_id: str) -> Response:
        """Manually complete a referral"""
        def operation():
            service = AdminReferralService()
            result = service.complete_referral(
                referral_id=referral_id,
                admin_user=request.user
            )
            
            return result
        
        return self.handle_service_operation(
            operation,
            success_message="Referral completed successfully",
            error_message="Failed to complete referral",
            operation_context="Admin complete referral"
        )


# ============================================================
# Leaderboard Views
# ============================================================

@referral_admin_router.register(
    r"admin/users/leaderboard", 
    name="admin-leaderboard"
)
@extend_schema(
    tags=["Admin - Leaderboard"],
    summary="User Leaderboard",
    description="Get user leaderboard with various categories and time periods (Staff only)",
    parameters=[admin_serializers.LeaderboardFiltersSerializer],
    responses={200: BaseResponseSerializer}
)
class AdminLeaderboardView(GenericAPIView, BaseAPIView):
    """Admin leaderboard"""
    serializer_class = admin_serializers.LeaderboardFiltersSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get leaderboard"""
        def operation():
            # Parse filters
            filter_serializer = admin_serializers.LeaderboardFiltersSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminLeaderboardService()
            leaderboard_data = service.get_leaderboard(
                category=filter_serializer.validated_data.get('category', 'overall'),
                period=filter_serializer.validated_data.get('period', 'all_time'),
                limit=filter_serializer.validated_data.get('limit', 100)
            )
            
            # Serialize the leaderboard
            leaderboard_serializer = UserLeaderboardSerializer(
                leaderboard_data['leaderboard'],
                many=True
            )
            
            result = {
                'leaderboard': leaderboard_serializer.data,
                'category': leaderboard_data['category'],
                'period': leaderboard_data['period'],
                'total_users': leaderboard_data['total_users']
            }
            
            return result
        
        return self.handle_service_operation(
            operation,
            success_message="Leaderboard retrieved successfully",
            error_message="Failed to retrieve leaderboard",
            operation_context="Admin leaderboard"
        )
