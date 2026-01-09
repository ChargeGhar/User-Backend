"""
Admin achievement management views
============================================================

This module contains views for admin achievement management operations.

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
from api.admin.services import AdminAchievementService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission

achievement_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)


# ============================================================
# Achievement Management Views
# ============================================================
# NOTE: Analytics route must be registered BEFORE the detail route
# to avoid URL pattern conflicts

@achievement_admin_router.register(
    r"admin/achievements/analytics", 
    name="admin-achievement-analytics"
)
@extend_schema(
    tags=["Admin - Achievements"],
    summary="Achievement Analytics",
    description="Get comprehensive achievement analytics (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminAchievementAnalyticsView(GenericAPIView, BaseAPIView):
    """Admin achievement analytics"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get achievement analytics"""
        def operation():
            service = AdminAchievementService()
            analytics = service.get_achievement_analytics()
            
            return analytics
        
        return self.handle_service_operation(
            operation,
            success_message="Achievement analytics retrieved successfully",
            error_message="Failed to retrieve achievement analytics",
            operation_context="Admin achievement analytics"
        )


@achievement_admin_router.register(r"admin/achievements", name="admin-achievements")
@extend_schema(
    tags=["Admin - Achievements"],
    summary="Achievement Management",
    description="Manage achievements - list and create (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminAchievementsView(GenericAPIView, BaseAPIView):
    """Admin achievement management"""
    serializer_class = serializers.AchievementFiltersSerializer
    permission_classes = [IsStaffPermission]

    @extend_schema(
        summary="List Achievements",
        description="Get paginated list of achievements with filters",
        parameters=[serializers.AchievementFiltersSerializer]
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get achievement list with filters"""
        def operation():
            # Parse filters
            filter_serializer = serializers.AchievementFiltersSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            
            filters = {
                'criteria_type': filter_serializer.validated_data.get('criteria_type'),
                'is_active': filter_serializer.validated_data.get('is_active'),
                'search': filter_serializer.validated_data.get('search'),
                'page': filter_serializer.validated_data.get('page', 1),
                'page_size': filter_serializer.validated_data.get('page_size', 20)
            }
            
            service = AdminAchievementService()
            paginated_result = service.get_all_achievements(filters)
            
            # Serialize the achievements with admin statistics
            achievement_serializer = serializers.AdminAchievementSerializer(
                paginated_result['results'],
                many=True
            )
            paginated_result['results'] = achievement_serializer.data
            
            return paginated_result
        
        return self.handle_service_operation(
            operation,
            success_message="Achievements retrieved successfully",
            error_message="Failed to retrieve achievements",
            operation_context="Admin list achievements"
        )

    @extend_schema(
        summary="Create Achievement",
        description="Create a new achievement",
        request=serializers.CreateAchievementSerializer
    )
    @log_api_call(include_request_data=True)
    def post(self, request: Request) -> Response:
        """Create achievement"""
        def operation():
            create_serializer = serializers.CreateAchievementSerializer(
                data=request.data
            )
            create_serializer.is_valid(raise_exception=True)
            
            service = AdminAchievementService()
            achievement = service.create_achievement(
                name=create_serializer.validated_data['name'],
                description=create_serializer.validated_data['description'],
                criteria_type=create_serializer.validated_data['criteria_type'],
                criteria_value=create_serializer.validated_data['criteria_value'],
                reward_type=create_serializer.validated_data['reward_type'],
                reward_value=create_serializer.validated_data['reward_value'],
                admin_user=request.user
            )
            
            # Reload with statistics
            from api.user.social.models import Achievement
            from django.db.models import Count, Q
            achievement = Achievement.objects.annotate(
                total_unlocked=Count(
                    'userachievement',
                    filter=Q(userachievement__is_unlocked=True)
                ),
                total_claimed=Count(
                    'userachievement',
                    filter=Q(userachievement__is_claimed=True)
                ),
                total_users_progress=Count('userachievement', distinct=True)
            ).get(id=achievement.id)
            
            achievement_serializer = serializers.AdminAchievementSerializer(achievement)
            return achievement_serializer.data
        
        result = self.handle_service_operation(
            operation,
            success_message="Achievement created successfully",
            error_message="Failed to create achievement",
            operation_context="Admin create achievement"
        )
        result.status_code = status.HTTP_201_CREATED
        return result


@achievement_admin_router.register(
    r"admin/achievements/<str:achievement_id>", 
    name="admin-achievement-detail"
)
@extend_schema(
    tags=["Admin - Achievements"],
    summary="Achievement Details",
    description="Get, update, or delete a specific achievement (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminAchievementDetailView(GenericAPIView, BaseAPIView):
    """Admin achievement detail operations"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        summary="Get Achievement Details",
        description="Get details of a specific achievement"
    )
    @log_api_call()
    def get(self, request: Request, achievement_id: str) -> Response:
        """Get achievement details"""
        def operation():
            from api.user.social.models import Achievement
            from django.db.models import Count, Q
            
            achievement = Achievement.objects.annotate(
                total_unlocked=Count(
                    'userachievement',
                    filter=Q(userachievement__is_unlocked=True)
                ),
                total_claimed=Count(
                    'userachievement',
                    filter=Q(userachievement__is_claimed=True)
                ),
                total_users_progress=Count('userachievement', distinct=True)
            ).get(id=achievement_id)
            
            achievement_serializer = serializers.AdminAchievementSerializer(achievement)
            
            return achievement_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Achievement retrieved successfully",
            error_message="Failed to retrieve achievement",
            operation_context="Admin get achievement"
        )

    @extend_schema(
        summary="Update Achievement",
        description="Update an existing achievement",
        request=serializers.UpdateAchievementSerializer
    )
    @log_api_call(include_request_data=True)
    def put(self, request: Request, achievement_id: str) -> Response:
        """Update achievement"""
        def operation():
            update_serializer = serializers.UpdateAchievementSerializer(
                data=request.data
            )
            update_serializer.is_valid(raise_exception=True)
            
            service = AdminAchievementService()
            achievement = service.update_achievement(
                achievement_id=achievement_id,
                update_data=update_serializer.validated_data,
                admin_user=request.user
            )
            
            # Reload with statistics
            from api.user.social.models import Achievement
            from django.db.models import Count, Q
            achievement = Achievement.objects.annotate(
                total_unlocked=Count(
                    'userachievement',
                    filter=Q(userachievement__is_unlocked=True)
                ),
                total_claimed=Count(
                    'userachievement',
                    filter=Q(userachievement__is_claimed=True)
                ),
                total_users_progress=Count('userachievement', distinct=True)
            ).get(id=achievement.id)
            
            achievement_serializer = serializers.AdminAchievementSerializer(achievement)
            return achievement_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Achievement updated successfully",
            error_message="Failed to update achievement",
            operation_context="Admin update achievement"
        )

    @extend_schema(
        summary="Delete Achievement",
        description="Delete (deactivate) an achievement"
    )
    @log_api_call()
    def delete(self, request: Request, achievement_id: str) -> Response:
        """Delete achievement"""
        def operation():
            service = AdminAchievementService()
            result = service.delete_achievement(
                achievement_id=achievement_id,
                admin_user=request.user
            )
            
            return result
        
        return self.handle_service_operation(
            operation,
            success_message="Achievement deleted successfully",
            error_message="Failed to delete achievement",
            operation_context="Admin delete achievement"
        )
