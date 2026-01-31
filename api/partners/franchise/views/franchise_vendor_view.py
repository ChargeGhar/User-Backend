"""
Franchise Vendor Views

POST /api/partner/franchise/vendors/ - Create vendor
GET /api/partner/franchise/vendors/ - List vendors
GET /api/partner/franchise/vendors/{id}/ - Vendor details
PATCH /api/partner/franchise/vendors/{id}/ - Update vendor
PATCH /api/partner/franchise/vendors/{id}/status/ - Update vendor status
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
from api.partners.franchise.serializers import (
    FranchiseVendorListSerializer,
    CreateVendorSerializer,
    UpdateVendorSerializer,
    UpdateVendorStatusSerializer,
)
from api.partners.franchise.services import FranchiseVendorService

franchise_vendor_router = CustomViewRouter()


@franchise_vendor_router.register(r"partner/franchise/vendors", name="franchise-vendors")
class FranchiseVendorView(GenericAPIView, BaseAPIView):
    """Franchise vendor management"""
    permission_classes = [IsFranchise]
    
    @extend_schema(
        tags=["Partner - Franchise"],
        summary="List Vendors",
        description="""
        List franchise's own vendors
        
        Business Rules:
        - BR10.2: Only own vendors
        """,
        parameters=[
            OpenApiParameter('page', type=int, description='Page number'),
            OpenApiParameter('page_size', type=int, description='Items per page'),
            OpenApiParameter('vendor_type', type=str, description='Filter: REVENUE or NON_REVENUE'),
            OpenApiParameter('status', type=str, description='Filter: ACTIVE, INACTIVE, SUSPENDED'),
            OpenApiParameter('search', type=str, description='Search by name, code, phone'),
        ],
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """List own vendors"""
        def operation():
            franchise = request.user.partner_profile
            filters = {
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
                'vendor_type': request.query_params.get('vendor_type'),
                'status': request.query_params.get('status'),
                'search': request.query_params.get('search'),
            }
            service = FranchiseVendorService()
            return service.get_vendors_list(franchise, filters)
        
        return self.handle_service_operation(
            operation,
            "Vendors retrieved successfully",
            "Failed to retrieve vendors"
        )
    
    @extend_schema(
        tags=["Partner - Franchise"],
        summary="Create Vendor",
        description="""
        Create new sub-vendor under franchise
        
        Business Rules:
        - BR1.5: Franchise creates own vendors
        - BR2.2: Franchise assigns stations to vendors
        """,
        request=CreateVendorSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create sub-vendor"""
        def operation():
            franchise = request.user.partner_profile
            serializer = CreateVendorSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = FranchiseVendorService()
            vendor = service.create_vendor(
                franchise=franchise,
                **serializer.validated_data
            )
            
            return {
                'id': vendor.id,
                'code': vendor.code,
                'business_name': vendor.business_name,
                'vendor_type': vendor.vendor_type,
                'status': vendor.status,
            }
        
        return self.handle_service_operation(
            operation,
            "Vendor created successfully",
            "Failed to create vendor"
        )


@franchise_vendor_router.register(
    r"partner/franchise/vendors/<uuid:vendor_id>",
    name="franchise-vendor-detail"
)
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Get Vendor Details",
    description="Get detailed information about a specific vendor",
    responses={200: BaseResponseSerializer}
)
class FranchiseVendorDetailView(GenericAPIView, BaseAPIView):
    """Vendor details"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request, vendor_id: str) -> Response:
        """Get vendor details"""
        def operation():
            franchise = request.user.partner_profile
            service = FranchiseVendorService()
            return service.get_vendor_detail(franchise, vendor_id)
        
        return self.handle_service_operation(
            operation,
            "Vendor details retrieved successfully",
            "Failed to retrieve vendor details"
        )
    
    @log_api_call()
    def patch(self, request: Request, vendor_id: str) -> Response:
        """Update vendor"""
        def operation():
            franchise = request.user.partner_profile
            serializer = UpdateVendorSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = FranchiseVendorService()
            vendor = service.update_vendor(franchise, vendor_id, serializer.validated_data)
            
            return {
                'id': vendor.id,
                'code': vendor.code,
                'business_name': vendor.business_name,
                'contact_phone': vendor.contact_phone,
                'contact_email': vendor.contact_email,
                'address': vendor.address,
                'updated_at': vendor.updated_at,
            }
        
        return self.handle_service_operation(
            operation,
            "Vendor updated successfully",
            "Failed to update vendor"
        )


@franchise_vendor_router.register(
    r"partner/franchise/vendors/<uuid:vendor_id>/status",
    name="franchise-vendor-status"
)
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Update Vendor Status",
    description="Activate, suspend, or deactivate a vendor",
    request=UpdateVendorStatusSerializer,
    responses={200: BaseResponseSerializer}
)
class FranchiseVendorStatusView(GenericAPIView, BaseAPIView):
    """Update vendor status"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def patch(self, request: Request, vendor_id: str) -> Response:
        """Update vendor status"""
        def operation():
            franchise = request.user.partner_profile
            serializer = UpdateVendorStatusSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = FranchiseVendorService()
            vendor = service.update_vendor_status(
                franchise,
                vendor_id,
                serializer.validated_data['status'],
                serializer.validated_data.get('reason')
            )
            
            return {
                'id': vendor.id,
                'code': vendor.code,
                'status': vendor.status,
                'updated_at': vendor.updated_at,
            }
        
        return self.handle_service_operation(
            operation,
            "Vendor status updated successfully",
            "Failed to update vendor status"
        )
