"""
Franchise Agreement View
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
from api.partners.franchise.services import FranchiseAgreementService
from api.partners.franchise.serializers import AgreementsResponseSerializer

franchise_agreement_router = CustomViewRouter()


@franchise_agreement_router.register(r"partner/franchise/agreements", name="franchise-agreements")
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Get Agreements",
    description="""
    Get franchise agreement with ChargeGhar and all vendor agreements.
    
    Returns:
    - Franchise agreement: revenue share %, upfront payment, balance, stats
    - Vendor agreements: revenue model (PERCENTAGE/FIXED), share %, fixed amount
    
    Business Rules:
    - BR3.5: Franchise revenue share % with ChargeGhar
    - BR3.3: Vendor revenue model (Fixed OR Percentage)
    - BR3.4: Non-Revenue vendors have no revenue model
    """,
    responses={200: BaseResponseSerializer}
)
class FranchiseAgreementsView(GenericAPIView, BaseAPIView):
    """Get franchise and vendor agreements"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get agreements"""
        def operation():
            franchise = request.user.partner_profile
            service = FranchiseAgreementService()
            result = service.get_agreements(franchise)
            
            serializer = AgreementsResponseSerializer(result)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Agreements retrieved successfully",
            "Failed to retrieve agreements"
        )
