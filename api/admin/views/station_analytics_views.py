"""
Station Analytics Views
"""
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView

from api.common.mixins import BaseAPIView
from api.user.auth.permissions import IsStaffPermission
from api.common.serializers import BaseResponseSerializer
from api.admin.services.station_analytics_service import StationAnalyticsService
from api.admin.serializers.analytics_serializers import StationAnalyticsResponseSerializer
from api.common.routers import CustomViewRouter

station_analytics_router = CustomViewRouter()


@station_analytics_router.register("admin/analytics/station-performance", name="admin-station-analytics")
class StationAnalyticsView(GenericAPIView, BaseAPIView):
    """
    Get comprehensive station performance analytics
    
    Returns top performing stations by revenue, utilization rates, and trends
    """
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=["Admin - Analytics"],
        summary="Get Station Performance Analytics",
        description="Retrieve station performance metrics including utilization rates, revenue, and top performing stations",
        responses={
            200: StationAnalyticsResponseSerializer,
            400: BaseResponseSerializer
        }
    )
    def get(self, request):
        """Get station analytics"""
        analytics_data = StationAnalyticsService.get_station_analytics()
        
        return self.success_response(
            data=analytics_data,
            message="Station performance analytics retrieved successfully"
        )
