# api/admin/views/partner_views.py
"""
Admin Partner Management Views

Endpoints for admin partner management operations.
Based on Endpoints.md Section 1.1-1.4
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin.serializers import partner_serializers as serializers
from api.admin.services.admin_partner_service import AdminPartnerService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission

partner_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Partner Management (Section 1.1)
# ============================================================================
# IMPORTANT: Route order matters! Specific routes MUST be registered BEFORE generic ones.
# The generic route admin/partners/<partner_id> would match "franchise", "vendor", etc.

@partner_admin_router.register(r"admin/partners/franchise", name="admin-partners-create-franchise")
class AdminCreateFranchiseView(GenericAPIView, BaseAPIView):
    """Create franchise partner"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.CreateFranchiseSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Create Franchise",
        description="Create a new franchise partner with station assignments",
        request=serializers.CreateFranchiseSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create new franchise partner"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            service = AdminPartnerService()
            partner = service.create_franchise(
                user_id=data['user_id'],
                business_name=data['business_name'],
                contact_phone=data['contact_phone'],
                revenue_share_percent=data['revenue_share_percent'],
                password=data['password'],
                admin_user=request.user,
                contact_email=data.get('contact_email'),
                address=data.get('address'),
                upfront_amount=data.get('upfront_amount', 0),
                station_ids=data.get('station_ids', []),
                notes=data.get('notes')
            )
            
            return serializers.AdminPartnerDetailSerializer(partner).data
        
        return self.handle_service_operation(
            operation,
            "Franchise created successfully",
            "Failed to create franchise"
        )


@partner_admin_router.register(r"admin/partners/vendor", name="admin-partners-create-vendor")
class AdminCreateVendorView(GenericAPIView, BaseAPIView):
    """Create vendor partner (ChargeGhar-level)"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.CreateVendorSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Create Vendor",
        description="Create a new ChargeGhar-level vendor partner with station assignments (multiple stations supported)",
        request=serializers.CreateVendorSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create new vendor partner"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            service = AdminPartnerService()
            partner = service.create_vendor(
                user_id=data['user_id'],
                vendor_type=data['vendor_type'],
                business_name=data['business_name'],
                contact_phone=data['contact_phone'],
                station_ids=data['station_ids'],
                admin_user=request.user,
                contact_email=data.get('contact_email'),
                address=data.get('address'),
                revenue_model=data.get('revenue_model'),
                partner_percent=data.get('partner_percent'),
                fixed_amount=data.get('fixed_amount'),
                password=data.get('password'),
                notes=data.get('notes')
            )
            
            return serializers.AdminPartnerDetailSerializer(partner).data
        
        return self.handle_service_operation(
            operation,
            "Vendor created successfully",
            "Failed to create vendor"
        )


@partner_admin_router.register(r"admin/partners/stations/assign", name="admin-partners-stations-assign")
class AdminAssignStationsToVendorView(GenericAPIView, BaseAPIView):
    """Assign stations to existing vendor"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.AssignStationsToVendorSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Assign Stations to Vendor",
        description="Assign one or more stations to an existing vendor. Copies the vendor's existing revenue configuration.",
        request=serializers.AssignStationsToVendorSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Assign stations to existing vendor"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            service = AdminPartnerService()
            distributions = service.assign_stations_to_vendor(
                vendor_id=str(data['vendor_id']),
                station_ids=data['station_ids'],
                admin_user=request.user,
                notes=data.get('notes')
            )
            
            return [
                serializers.AdminStationDistributionSerializer(d).data
                for d in distributions
            ]
        
        return self.handle_service_operation(
            operation,
            "Stations assigned to vendor successfully",
            "Failed to assign stations to vendor"
        )


# ============================================================================
# Station Distribution (Section 1.2)
# ============================================================================

@partner_admin_router.register(r"admin/partners/stations", name="admin-partners-stations")
class AdminStationDistributionListView(GenericAPIView, BaseAPIView):
    """Station distribution list"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        tags=["Admin - Partners"],
        summary="List Station Distributions",
        description="Get paginated list of station-partner assignments",
        parameters=[
            OpenApiParameter(name='station_id', type=str),
            OpenApiParameter(name='partner_id', type=str),
            OpenApiParameter(name='distribution_type', type=str, 
                           enum=['CHARGEGHAR_TO_FRANCHISE', 'CHARGEGHAR_TO_VENDOR', 'FRANCHISE_TO_VENDOR']),
            OpenApiParameter(name='is_active', type=bool, default=True),
            OpenApiParameter(name='page', type=int, default=1),
            OpenApiParameter(name='page_size', type=int, default=20),
        ],
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get station distributions list"""
        def operation():
            filter_serializer = serializers.AdminStationDistributionFilterSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminPartnerService()
            result = service.get_station_distributions(filter_serializer.validated_data)
            
            if result and 'results' in result:
                result['results'] = serializers.AdminStationDistributionSerializer(
                    result['results'], many=True
                ).data
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Station distributions retrieved successfully",
            "Failed to retrieve station distributions"
        )


@partner_admin_router.register(r"admin/partners/stations/available", name="admin-partners-stations-available")
class AdminAvailableStationsView(GenericAPIView, BaseAPIView):
    """Available (unassigned) stations"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        tags=["Admin - Partners"],
        summary="List Available Stations",
        description="Get list of stations not assigned to any partner",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get available stations"""
        def operation():
            service = AdminPartnerService()
            stations = service.get_available_stations()
            
            # Return basic station info
            return [
                {
                    'id': str(s.id),
                    'station_name': s.station_name,
                    'serial_number': s.serial_number,
                    'address': s.address,
                    'status': s.status
                }
                for s in stations
            ]
        
        return self.handle_service_operation(
            operation,
            "Available stations retrieved successfully",
            "Failed to retrieve available stations"
        )


@partner_admin_router.register(
    r"admin/partners/stations/<str:distribution_id>", 
    name="admin-partners-stations-detail"
)
class AdminStationDistributionDetailView(GenericAPIView, BaseAPIView):
    """Station distribution deactivation"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Deactivate Station Distribution",
        description="Deactivate a station-partner assignment",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def delete(self, request: Request, distribution_id: str) -> Response:
        """Deactivate station distribution"""
        def operation():
            service = AdminPartnerService()
            distribution = service.deactivate_station_distribution(
                distribution_id=distribution_id,
                admin_user=request.user
            )
            return serializers.AdminStationDistributionSerializer(distribution).data
        
        return self.handle_service_operation(
            operation,
            "Station distribution deactivated successfully",
            "Failed to deactivate station distribution"
        )


# ============================================================================
# Payout Management (Section 1.4)
# ============================================================================

@partner_admin_router.register(r"admin/partners/payouts", name="admin-partners-payouts")
class AdminPayoutListView(GenericAPIView, BaseAPIView):
    """Payout requests list"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        tags=["Admin - Partners"],
        summary="List Payout Requests",
        description="Get paginated list of payout requests (ChargeGhar payouts only)",
        parameters=[
            OpenApiParameter(name='payout_type', type=str,
                           enum=['CHARGEGHAR_TO_FRANCHISE', 'CHARGEGHAR_TO_VENDOR']),
            OpenApiParameter(name='status', type=str,
                           enum=['PENDING', 'APPROVED', 'PROCESSING', 'COMPLETED', 'REJECTED']),
            OpenApiParameter(name='partner_id', type=str),
            OpenApiParameter(name='page', type=int, default=1),
            OpenApiParameter(name='page_size', type=int, default=20),
        ],
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get payout requests list"""
        def operation():
            filter_serializer = serializers.AdminPayoutListFilterSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminPartnerService()
            result = service.get_payouts_list(filter_serializer.validated_data)
            
            if result and 'results' in result:
                result['results'] = serializers.AdminPayoutSerializer(
                    result['results'], many=True
                ).data
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Payout requests retrieved successfully",
            "Failed to retrieve payout requests"
        )


@partner_admin_router.register(r"admin/partners/payouts/<str:payout_id>", name="admin-partners-payouts-detail")
class AdminPayoutDetailView(GenericAPIView, BaseAPIView):
    """Payout request detail"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Get Payout Details",
        description="Get detailed information about a payout request",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request, payout_id: str) -> Response:
        """Get payout details"""
        def operation():
            service = AdminPartnerService()
            payout = service.get_payout_detail(payout_id)
            return serializers.AdminPayoutDetailSerializer(payout).data
        
        return self.handle_service_operation(
            operation,
            "Payout retrieved successfully",
            "Failed to retrieve payout"
        )


@partner_admin_router.register(
    r"admin/partners/payouts/<str:payout_id>/approve", 
    name="admin-partners-payouts-approve"
)
class AdminPayoutApproveView(GenericAPIView, BaseAPIView):
    """Approve payout request"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.AdminPayoutActionSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Approve Payout",
        description="Approve a pending payout request",
        request=serializers.AdminPayoutActionSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, payout_id: str) -> Response:
        """Approve payout"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminPartnerService()
            payout = service.approve_payout(
                payout_id=payout_id,
                admin_user=request.user,
                admin_notes=serializer.validated_data.get('admin_notes')
            )
            return serializers.AdminPayoutDetailSerializer(payout).data
        
        return self.handle_service_operation(
            operation,
            "Payout approved successfully",
            "Failed to approve payout"
        )


@partner_admin_router.register(
    r"admin/partners/payouts/<str:payout_id>/process", 
    name="admin-partners-payouts-process"
)
class AdminPayoutProcessView(GenericAPIView, BaseAPIView):
    """Mark payout as processing"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.AdminPayoutActionSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Process Payout",
        description="Mark an approved payout as processing",
        request=serializers.AdminPayoutActionSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, payout_id: str) -> Response:
        """Mark payout as processing"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminPartnerService()
            payout = service.process_payout(
                payout_id=payout_id,
                admin_user=request.user,
                admin_notes=serializer.validated_data.get('admin_notes')
            )
            return serializers.AdminPayoutDetailSerializer(payout).data
        
        return self.handle_service_operation(
            operation,
            "Payout marked as processing",
            "Failed to process payout"
        )


@partner_admin_router.register(
    r"admin/partners/payouts/<str:payout_id>/complete", 
    name="admin-partners-payouts-complete"
)
class AdminPayoutCompleteView(GenericAPIView, BaseAPIView):
    """Complete payout"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.AdminPayoutActionSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Complete Payout",
        description="Complete a processing payout and deduct from partner balance",
        request=serializers.AdminPayoutActionSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, payout_id: str) -> Response:
        """Complete payout"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminPartnerService()
            payout = service.complete_payout(
                payout_id=payout_id,
                admin_user=request.user,
                admin_notes=serializer.validated_data.get('admin_notes')
            )
            return serializers.AdminPayoutDetailSerializer(payout).data
        
        return self.handle_service_operation(
            operation,
            "Payout completed successfully",
            "Failed to complete payout"
        )


@partner_admin_router.register(
    r"admin/partners/payouts/<str:payout_id>/reject", 
    name="admin-partners-payouts-reject"
)
class AdminPayoutRejectView(GenericAPIView, BaseAPIView):
    """Reject payout request"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.AdminPayoutRejectSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Reject Payout",
        description="Reject a payout request with reason",
        request=serializers.AdminPayoutRejectSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, payout_id: str) -> Response:
        """Reject payout"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            service = AdminPartnerService()
            payout = service.reject_payout(
                payout_id=payout_id,
                admin_user=request.user,
                rejection_reason=data['rejection_reason'],
                admin_notes=data.get('admin_notes')
            )
            return serializers.AdminPayoutDetailSerializer(payout).data
        
        return self.handle_service_operation(
            operation,
            "Payout rejected successfully",
            "Failed to reject payout"
        )


# ============================================================================
# Generic Partner Routes (MUST BE LAST - after all specific routes)
# ============================================================================

@partner_admin_router.register(r"admin/partners/<str:partner_id>/status", name="admin-partners-status")
class AdminPartnerStatusView(GenericAPIView, BaseAPIView):
    """Partner status management"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.UpdatePartnerStatusSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Update Partner Status",
        description="Activate, suspend, or deactivate a partner",
        request=serializers.UpdatePartnerStatusSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, partner_id: str) -> Response:
        """Update partner status"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            service = AdminPartnerService()
            partner = service.update_partner_status(
                partner_id=partner_id,
                status=data['status'],
                admin_user=request.user,
                reason=data.get('reason')
            )
            
            return serializers.AdminPartnerDetailSerializer(partner).data
        
        return self.handle_service_operation(
            operation,
            "Partner status updated successfully",
            "Failed to update partner status"
        )


@partner_admin_router.register(
    r"admin/partners/<str:partner_id>/reset-password",
    name="admin-partners-reset-password"
)
class AdminPartnerResetPasswordView(GenericAPIView, BaseAPIView):
    """Reset partner password (admin action)"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.AdminResetPartnerPasswordSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Reset Partner Password",
        description="Reset password for a partner (used when partner forgets password)",
        request=serializers.AdminResetPartnerPasswordSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, partner_id: str) -> Response:
        """Reset partner password"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminPartnerService()
            partner = service.reset_partner_password(
                partner_id=partner_id,
                new_password=serializer.validated_data['new_password'],
                admin_user=request.user
            )
            
            return serializers.AdminPartnerDetailSerializer(partner).data
        
        return self.handle_service_operation(
            operation,
            "Partner password reset successfully",
            "Failed to reset partner password"
        )


@partner_admin_router.register(
    r"admin/partners/<str:partner_id>/vendor-type",
    name="admin-partners-vendor-type"
)
class AdminChangeVendorTypeView(GenericAPIView, BaseAPIView):
    """Change vendor type (NON_REVENUE <-> REVENUE)"""
    permission_classes = [IsStaffPermission]
    serializer_class = serializers.ChangeVendorTypeSerializer

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Change Vendor Type",
        description="""
        Change vendor type between REVENUE and NON_REVENUE.
        
        **NON_REVENUE -> REVENUE:**
        - Requires password (for dashboard access)
        - Requires revenue_model (PERCENTAGE or FIXED)
        - Requires partner_percent or fixed_amount based on model
        
        **REVENUE -> NON_REVENUE:**
        - No additional fields required
        - Revenue share will be deleted
        - Dashboard access will be revoked via permissions
        """,
        request=serializers.ChangeVendorTypeSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, partner_id: str) -> Response:
        """Change vendor type"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            service = AdminPartnerService()
            partner = service.change_vendor_type(
                partner_id=partner_id,
                new_vendor_type=data['vendor_type'],
                admin_user=request.user,
                password=data.get('password'),
                revenue_model=data.get('revenue_model'),
                partner_percent=data.get('partner_percent'),
                fixed_amount=data.get('fixed_amount'),
                reason=data.get('reason')
            )
            
            return serializers.AdminPartnerDetailSerializer(partner).data
        
        return self.handle_service_operation(
            operation,
            "Vendor type changed successfully",
            "Failed to change vendor type"
        )


@partner_admin_router.register(r"admin/partners/<str:partner_id>", name="admin-partners-detail")
class AdminPartnerDetailView(GenericAPIView, BaseAPIView):
    """Partner detail, update operations"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Get Partner Details",
        description="Get detailed information about a specific partner",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request, partner_id: str) -> Response:
        """Get partner details"""
        def operation():
            service = AdminPartnerService()
            partner = service.get_partner_detail(partner_id)
            return serializers.AdminPartnerDetailSerializer(partner).data
        
        return self.handle_service_operation(
            operation,
            "Partner retrieved successfully",
            "Failed to retrieve partner"
        )

    @extend_schema(
        tags=["Admin - Partners"],
        summary="Update Partner",
        description="Update partner details (business name, contact info, etc.)",
        request=serializers.UpdatePartnerSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, partner_id: str) -> Response:
        """Update partner details"""
        def operation():
            serializer = serializers.UpdatePartnerSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminPartnerService()
            partner = service.update_partner(
                partner_id=partner_id,
                data=serializer.validated_data,
                admin_user=request.user
            )
            
            return serializers.AdminPartnerDetailSerializer(partner).data
        
        return self.handle_service_operation(
            operation,
            "Partner updated successfully",
            "Failed to update partner"
        )


@partner_admin_router.register(r"admin/partners", name="admin-partners")
class AdminPartnerListView(GenericAPIView, BaseAPIView):
    """Partner list - MUST BE LAST to not override specific routes"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        tags=["Admin - Partners"],
        summary="List All Partners",
        description="Get paginated list of all partners (franchises & vendors) with filters",
        parameters=[
            OpenApiParameter(name='partner_type', type=str, enum=['FRANCHISE', 'VENDOR']),
            OpenApiParameter(name='vendor_type', type=str, enum=['REVENUE', 'NON_REVENUE']),
            OpenApiParameter(name='status', type=str, enum=['PENDING', 'ACTIVE', 'INACTIVE', 'SUSPENDED']),
            OpenApiParameter(name='parent_id', type=str, description='Filter by franchise ID'),
            OpenApiParameter(name='search', type=str, description='Search by name, code, phone'),
            OpenApiParameter(name='page', type=int, default=1),
            OpenApiParameter(name='page_size', type=int, default=20),
        ],
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get partners list with filters"""
        def operation():
            filter_serializer = serializers.AdminPartnerListFilterSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminPartnerService()
            result = service.get_partners_list(filter_serializer.validated_data)
            
            if result and 'results' in result:
                result['results'] = serializers.AdminPartnerSerializer(
                    result['results'], many=True
                ).data
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Partners retrieved successfully",
            "Failed to retrieve partners"
        )
