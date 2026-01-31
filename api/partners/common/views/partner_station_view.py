"""
Partner Station Views (Common for both Franchise and Vendor)

GET /api/partner/stations/ - List own stations
GET /api/partner/stations/{id}/ - Station details
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.permissions import HasDashboardAccess
from api.partners.common.services import PartnerStationService

partner_station_router = CustomViewRouter()


@partner_station_router.register(r"partner/stations", name="partner-stations-list")
@extend_schema(
    tags=["Partner - Common"],
    summary="List Own Stations",
    description="""
    Get paginated list of partner's own stations with revenue info.
    
    Works for both Franchise and Vendor partners.
    
    Business Rules Implemented:
    - BR10.2: Only own stations (filtered by partner_id)
    - BR12.2: Only own transactions
    - BR2.3: Vendor has only ONE station
    - Auto-detects distribution type based on partner type
    """,
    parameters=[
        OpenApiParameter('page', type=int, description='Page number (default: 1)'),
        OpenApiParameter('page_size', type=int, description='Items per page (default: 20, max: 100)'),
        OpenApiParameter('status', type=str, description='Filter by station status: ONLINE, OFFLINE, MAINTENANCE'),
        OpenApiParameter('search', type=str, description='Search by station_name, serial_number, address'),
        OpenApiParameter('has_vendor', type=bool, description='Filter: true=assigned to vendor, false=no vendor (Franchise only)'),
    ],
    responses={200: BaseResponseSerializer}
)
class PartnerStationListView(GenericAPIView, BaseAPIView):
    """List partner's own stations"""
    permission_classes = [HasDashboardAccess]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get stations list"""
        def operation():
            partner = request.user.partner_profile
            filters = {
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
                'status': request.query_params.get('status'),
                'search': request.query_params.get('search'),
                'has_vendor': request.query_params.get('has_vendor'),
            }
            service = PartnerStationService()
            return service.get_stations_list(partner, filters)
        
        return self.handle_service_operation(
            operation,
            "Stations retrieved successfully",
            "Failed to retrieve stations"
        )


@partner_station_router.register(
    r"partner/stations/<uuid:station_id>",
    name="partner-station-detail"
)
@extend_schema(
    tags=["Partner - Common"],
    summary="Get Station Details",
    description="""
    Get detailed station information including slots, powerbanks, media, and amenities.
    
    Works for both Franchise and Vendor partners.
    
    Business Rules Implemented:
    - BR10.2: Only own stations (access denied if not owned)
    - BR12.2: Only own data
    """,
    responses={200: BaseResponseSerializer}
)
class PartnerStationDetailView(GenericAPIView, BaseAPIView):
    """Get station details"""
    permission_classes = [HasDashboardAccess]
    
    @log_api_call()
    def get(self, request: Request, station_id: str) -> Response:
        """Get station details"""
        def operation():
            partner = request.user.partner_profile
            service = PartnerStationService()
            return service.get_station_detail(partner, station_id)
        
        return self.handle_service_operation(
            operation,
            "Station details retrieved successfully",
            "Failed to retrieve station details"
        )
