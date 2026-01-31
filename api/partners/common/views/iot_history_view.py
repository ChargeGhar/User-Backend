"""
Partner IoT History View - Shared by Franchise and Vendor
"""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.partners.auth.permissions import HasDashboardAccess
from api.partners.common.services import PartnerIoTService
from api.partners.vendor.serializers import IoTHistorySerializer

partner_iot_router = CustomViewRouter()


@partner_iot_router.register(r"partner/iot/history", name="partner-iot-history")
@extend_schema(
    tags=["Partner - IoT"],
    summary="Get IoT History",
    description="Get partner IoT action history",
    responses={200: IoTHistorySerializer(many=True)}
)
class PartnerIoTHistoryView(GenericAPIView, BaseAPIView):
    """IoT action history for partners"""
    permission_classes = [IsAuthenticated, HasDashboardAccess]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get IoT action history"""
        def operation():
            partner = request.user.partner
            service = PartnerIoTService()
            
            filters = {
                'action_type': request.query_params.get('action_type'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': int(request.query_params.get('page', 1)),
                'page_size': int(request.query_params.get('page_size', 20))
            }
            
            result = service.get_iot_history(partner, filters)
            serializer = IoTHistorySerializer(result['results'], many=True)
            
            return {
                'count': result['count'],
                'next': result['next'],
                'previous': result['previous'],
                'results': serializer.data
            }
        
        return self.handle_service_operation(
            operation,
            "IoT history retrieved successfully",
            "Failed to retrieve IoT history"
        )
