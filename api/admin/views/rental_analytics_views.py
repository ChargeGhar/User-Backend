"""
PowerBank Rental Analytics Views
"""
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin.services.rental_analytics_service import RentalAnalyticsService
from api.admin.serializers.rental_analytics_serializers import PowerBankRentalAnalyticsResponseSerializer
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.users.permissions import IsStaffPermission

rental_analytics_router = CustomViewRouter()


@rental_analytics_router.register(r"admin/analytics/powerbank-rentals", name="admin-powerbank-rentals-analytics")
class PowerBankRentalAnalyticsView(GenericAPIView, BaseAPIView):
    """PowerBank rental analytics endpoint"""
    permission_classes = [IsStaffPermission]
    serializer_class = PowerBankRentalAnalyticsResponseSerializer
    
    @extend_schema(
        tags=["Admin - Analytics"],
        summary="PowerBank Rental Analytics",
        description="""
        Get comprehensive powerbank rental analytics for dashboard visualization.
        
        **Features**:
        - Total powerbanks and rental statistics
        - Rental status distribution (completed, active, overdue, cancelled)
        - Top 10 powerbanks by rental cycles
        - Completion rate analysis (on-time vs late returns)
        - Chart-ready data format for frontend
        
        **Chart Data Included**:
        - Pie chart: Rental status distribution
        - Bar chart: Top powerbanks by cycles
        - Pie chart: On-time vs late completion
        
        **Use Cases**:
        - Dashboard KPI cards
        - Fleet utilization analysis
        - Performance monitoring
        - Business intelligence
        """,
        responses={200: PowerBankRentalAnalyticsResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get powerbank rental analytics"""
        def operation():
            service = RentalAnalyticsService()
            analytics = service.get_powerbank_rental_analytics()
            return analytics
        
        return self.handle_service_operation(
            operation,
            success_message="PowerBank rental analytics retrieved successfully",
            error_message="Failed to retrieve powerbank rental analytics"
        )
