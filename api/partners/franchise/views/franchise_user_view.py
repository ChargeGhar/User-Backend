"""
Franchise User Views

GET /api/partner/franchise/users/search/ - Search users for vendor creation
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.permissions import IsFranchise
from api.partners.franchise.services import FranchiseUserService

franchise_user_router = CustomViewRouter()


@franchise_user_router.register(r"partner/franchise/users/search", name="franchise-user-search")
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Search Users",
    description="""
    Search users for vendor creation
    
    Returns active users with profile data.
    Can exclude existing partners.
    """,
    parameters=[
        OpenApiParameter('search', type=str, description='Search by email, phone, username'),
        OpenApiParameter('exclude_partners', type=bool, description='Exclude existing partners (default: true)'),
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class FranchiseUserSearchView(GenericAPIView, BaseAPIView):
    """Search users for vendor creation"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Search users"""
        def operation():
            filters = {
                'search': request.query_params.get('search'),
                'exclude_partners': request.query_params.get('exclude_partners', 'true').lower() == 'true',
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            service = FranchiseUserService()
            return service.search_users_for_vendor(filters)
        
        return self.handle_service_operation(
            operation,
            "Users retrieved successfully",
            "Failed to retrieve users"
        )
