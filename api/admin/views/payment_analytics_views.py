"""
Payment Analytics Views
"""
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin.services.payment_analytics_service import PaymentAnalyticsService
from api.admin.serializers.payment_analytics_serializers import PaymentAnalyticsResponseSerializer
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.users.permissions import IsStaffPermission

payment_analytics_router = CustomViewRouter()


@payment_analytics_router.register(r"admin/analytics/payments", name="admin-payments-analytics")
class PaymentAnalyticsView(GenericAPIView, BaseAPIView):
    """Payment analytics endpoint"""
    permission_classes = [IsStaffPermission]
    serializer_class = PaymentAnalyticsResponseSerializer
    
    @extend_schema(
        tags=["Admin - Analytics"],
        summary="Payment Analytics",
        description="""
        Get comprehensive payment analytics for dashboard visualization.
        
        **Features**:
        - Total transactions and revenue statistics
        - Payment method distribution (wallet, gateway, points, combination)
        - Revenue breakdown by type (top-ups, rentals, fines)
        - Top 10 users by spending
        - Wallet analytics overview
        - Transaction breakdown with averages
        - Chart-ready data format for frontend
        
        **Chart Data Included**:
        - Pie chart: Payment method distribution
        - Bar chart: Revenue by transaction type
        - Bar chart: Top 10 users by spending
        
        **Use Cases**:
        - Financial dashboard
        - Revenue analysis
        - User behavior insights
        - Payment method preferences
        - Business intelligence
        """,
        responses={200: PaymentAnalyticsResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get payment analytics"""
        def operation():
            service = PaymentAnalyticsService()
            analytics = service.get_payment_analytics()
            return analytics
        
        return self.handle_service_operation(
            operation,
            success_message="Payment analytics retrieved successfully",
            error_message="Failed to retrieve payment analytics"
        )
