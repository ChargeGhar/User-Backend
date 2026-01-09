"""
Payment Analytics Views
"""
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView

from api.common.mixins import BaseAPIView
from api.user.auth.permissions import IsStaffPermission
from api.common.serializers import BaseResponseSerializer
from api.admin.services.payment_analytics_service import PaymentAnalyticsService
from api.admin.serializers.analytics_serializers import PaymentAnalyticsResponseSerializer
from api.common.routers import CustomViewRouter

payment_analytics_router = CustomViewRouter()


@payment_analytics_router.register("admin/analytics/payments", name="admin-payment-analytics")
class PaymentAnalyticsView(GenericAPIView, BaseAPIView):
    """
    Get comprehensive payment analytics
    
    Returns revenue breakdown, payment methods, gateway usage, and top performers
    """
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=["Admin - Analytics"],
        summary="Get Payment Analytics",
        description="Retrieve revenue analytics including payment methods, gateway usage, and top users by transaction amount",
        responses={
            200: PaymentAnalyticsResponseSerializer,
            400: BaseResponseSerializer
        }
    )
    def get(self, request):
        """Get payment analytics"""
        analytics_data = PaymentAnalyticsService.get_payment_analytics()
        
        return self.success_response(
            data=analytics_data,
            message="Payment analytics retrieved successfully"
        )
