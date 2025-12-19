"""
User Analytics Views
"""
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView

from api.common.mixins import BaseAPIView
from api.users.permissions import IsStaffPermission
from api.common.serializers import BaseResponseSerializer
from api.admin.services.user_analytics_service import UserAnalyticsService
from api.admin.serializers.analytics_serializers import UserAnalyticsResponseSerializer
from api.common.routers import CustomViewRouter

user_analytics_router = CustomViewRouter()


@user_analytics_router.register("admin/analytics/users", name="admin-user-analytics")
class UserAnalyticsView(GenericAPIView, BaseAPIView):
    """
    Get comprehensive user analytics data
    
    Returns user growth metrics, status distribution, and engagement statistics
    """
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=["Admin - Analytics"],
        summary="Get User Analytics",
        description="Retrieve comprehensive user growth, engagement, and status metrics",
        responses={
            200: UserAnalyticsResponseSerializer,
            400: BaseResponseSerializer
        }
    )
    def get(self, request):
        """Get user analytics"""
        analytics_data = UserAnalyticsService.get_user_analytics()
        
        return self.success_response(
            data=analytics_data,
            message="User analytics retrieved successfully"
        )
