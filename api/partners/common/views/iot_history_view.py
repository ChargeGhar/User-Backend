"""
Partner IoT History View - Shared by Franchise and Vendor
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.partners.auth.permissions import HasDashboardAccess
from api.partners.common.services import PartnerIoTService
from api.partners.common.serializers.iot_serializers import (
    IoTHistorySerializer,
    IoTHistoryListResponseSerializer,
)

partner_iot_router = CustomViewRouter()


@partner_iot_router.register(r"partner/iot/history", name="partner-iot-history")
@extend_schema(
    tags=["Partner - Common"],
    summary="Get IoT History",
    description="Get partner IoT action history",
    parameters=[
        OpenApiParameter('action_type', type=str, description='Filter by action type'),
        OpenApiParameter('start_date', type=str, description='Filter from date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', type=str, description='Filter to date (YYYY-MM-DD)'),
        OpenApiParameter('page', type=int, description='Page number (default: 1)'),
        OpenApiParameter('page_size', type=int, description='Items per page (default: 20, max: 100)'),
    ],
    responses={200: IoTHistoryListResponseSerializer}
)
class PartnerIoTHistoryView(GenericAPIView, BaseAPIView):
    """IoT action history for partners"""
    permission_classes = [IsAuthenticated, HasDashboardAccess]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get IoT action history"""
        def operation():
            partner = request.user.partner_profile
            service = PartnerIoTService()
            pagination_params = self.get_pagination_params(request)

            filters = {
                'action_type': request.query_params.get('action_type'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': pagination_params['page'],
                'page_size': pagination_params['page_size'],
            }
            paginated = service.get_iot_history(partner, filters)
            serializer = IoTHistorySerializer(paginated['results'], many=True)
            return {
                'results': serializer.data,
                'pagination': paginated['pagination'],
            }
        
        return self.handle_service_operation(
            operation,
            "IoT history retrieved successfully",
            "Failed to retrieve IoT history"
        )
