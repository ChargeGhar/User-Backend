"""
Franchise Dashboard View

GET /api/partner/franchise/dashboard/
"""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.permissions import IsFranchise
from api.partners.franchise.serializers import FranchiseDashboardSerializer
from api.partners.franchise.services import FranchiseService

franchise_dashboard_router = CustomViewRouter()


@franchise_dashboard_router.register(r"partner/franchise/dashboard", name="franchise-dashboard")
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Get Dashboard Statistics",
    description="""
    Returns aggregated dashboard statistics for the logged-in franchise.
    
    Business Rules Implemented:
    - BR3.5: franchise.revenue_share_percent
    - BR7.1: franchise_share from revenue distributions
    - BR10.2: Only own data (filtered by franchise_id)
    - BR12.2: Only own transactions
    """,
    responses={200: BaseResponseSerializer}
    )
class FranchiseDashboardView(GenericAPIView, BaseAPIView):
    """Franchise dashboard statistics"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get franchise dashboard stats"""
        def operation():
            franchise = request.user.partner_profile
            service = FranchiseService()
            return service.get_dashboard_stats(franchise)
        
        return self.handle_service_operation(
            operation,
            "Dashboard retrieved successfully",
            "Failed to retrieve dashboard"
        )