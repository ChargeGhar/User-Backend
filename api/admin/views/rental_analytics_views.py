"""
Rental Analytics Views
"""
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView

from api.common.mixins import BaseAPIView
from api.user.auth.permissions import IsStaffPermission
from api.common.serializers import BaseResponseSerializer
from api.admin.services.rental_analytics_service import RentalAnalyticsService
from api.admin.serializers.analytics_serializers import RentalAnalyticsResponseSerializer
from api.common.routers import CustomViewRouter

rental_analytics_router = CustomViewRouter()


@rental_analytics_router.register("admin/analytics/powerbank-rentals", name="admin-rental-analytics")
class RentalAnalyticsView(GenericAPIView, BaseAPIView):
    """
    Get comprehensive PowerBank rental analytics
    
    Returns rental status, payment methods, gateway breakdown, cycles, and trends
    """
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=["Admin - Analytics"],
        summary="Get PowerBank Rental Analytics",
        description="Retrieve rental statistics including status distribution, payment methods, and rental cycles",
        responses={
            200: RentalAnalyticsResponseSerializer,
            400: BaseResponseSerializer
        }
    )
    def get(self, request):
        """Get rental analytics"""
        analytics_data = RentalAnalyticsService.get_rental_analytics()
        
        return self.success_response(
            data=analytics_data,
            message="PowerBank rental analytics retrieved successfully"
        )
