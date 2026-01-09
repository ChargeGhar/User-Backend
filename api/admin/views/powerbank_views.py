"""
PowerBank administration operations - track and manage powerbank inventory
"""
import logging

from django.db.models import Q, Count, Avg
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers
from api.admin.services import AdminPowerBankService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission

powerbank_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@powerbank_router.register(r"admin/powerbanks", name="admin-powerbanks")
@extend_schema(
    tags=["Admin - PowerBanks"],
    summary="PowerBank Management",
    description="List and filter powerbanks with their current status and location (Staff only)",
    request=serializers.AdminPowerBankListSerializer,
    responses={200: BaseResponseSerializer}
)
class AdminPowerBankListView(GenericAPIView, BaseAPIView):
    """PowerBank management - list with filters"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get powerbanks list with filters"""
        def operation():
            filter_serializer = serializers.AdminPowerBankListSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminPowerBankService()
            result = service.get_powerbanks_list(filter_serializer.validated_data)
            
            return result
        
        return self.handle_service_operation(
            operation,
            "PowerBanks retrieved successfully",
            "Failed to retrieve powerbanks"
        )


@powerbank_router.register(r"admin/powerbanks/<str:powerbank_id>", name="admin-powerbank-detail")
class AdminPowerBankDetailView(GenericAPIView, BaseAPIView):
    """PowerBank detail view with rental history"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        operation_id="admin_powerbank_detail_retrieve",
        tags=["Admin - PowerBanks"],
        summary="Get PowerBank Detail",
        description="Get detailed powerbank information including rental history (Staff only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request, powerbank_id: str) -> Response:
        """Get powerbank detail"""
        def operation():
            service = AdminPowerBankService()
            powerbank_data = service.get_powerbank_detail(powerbank_id)
            
            return powerbank_data
        
        return self.handle_service_operation(
            operation,
            "PowerBank detail retrieved successfully",
            "Failed to retrieve powerbank detail"
        )


@powerbank_router.register(r"admin/powerbanks/<str:powerbank_id>/history", name="admin-powerbank-history")
@extend_schema(
    tags=["Admin - PowerBanks"],
    summary="PowerBank Rental History",
    description="Get complete rental history for a powerbank (Staff only)",
    request=serializers.AdminPowerBankHistorySerializer,
    responses={200: BaseResponseSerializer}
)
class AdminPowerBankHistoryView(GenericAPIView, BaseAPIView):
    """PowerBank rental history"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request, powerbank_id: str) -> Response:
        """Get powerbank rental history"""
        def operation():
            filter_serializer = serializers.AdminPowerBankHistorySerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminPowerBankService()
            result = service.get_powerbank_history(powerbank_id, filter_serializer.validated_data)
            
            return result
        
        return self.handle_service_operation(
            operation,
            "PowerBank history retrieved successfully",
            "Failed to retrieve powerbank history"
        )


@powerbank_router.register(r"admin/powerbanks/analytics/overview", name="admin-powerbanks-analytics")
@extend_schema(
    tags=["Admin - PowerBanks"],
    summary="PowerBank Analytics Overview",
    description="Get powerbank fleet analytics and statistics (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminPowerBankAnalyticsView(GenericAPIView, BaseAPIView):
    """PowerBank analytics overview"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get powerbank analytics"""
        def operation():
            service = AdminPowerBankService()
            analytics = service.get_powerbank_analytics()
            
            return analytics
        
        return self.handle_service_operation(
            operation,
            "PowerBank analytics retrieved successfully",
            "Failed to retrieve powerbank analytics"
        )


@powerbank_router.register(r"admin/powerbanks/<str:powerbank_id>/status", name="admin-powerbank-status")
@extend_schema(
    tags=["Admin - PowerBanks"],
    summary="Update PowerBank Status",
    description="Update powerbank status (AVAILABLE/MAINTENANCE/DAMAGED) (Staff only)",
    request=serializers.UpdatePowerBankStatusSerializer,
    responses={200: BaseResponseSerializer}
)
class UpdatePowerBankStatusView(GenericAPIView, BaseAPIView):
    """Update powerbank status"""
    serializer_class = serializers.UpdatePowerBankStatusSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def post(self, request: Request, powerbank_id: str) -> Response:
        """Update powerbank status"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminPowerBankService()
            powerbank = service.update_powerbank_status(
                powerbank_id,
                serializer.validated_data['status'],
                serializer.validated_data.get('reason', ''),
                request.user
            )
            
            return {
                'powerbank_id': str(powerbank['id']),
                'serial_number': powerbank['serial_number'],
                'new_status': powerbank['status'],
                'message': f'PowerBank status updated to {powerbank["status"]}'
            }
        
        return self.handle_service_operation(
            operation,
            "PowerBank status updated successfully",
            "Failed to update powerbank status"
        )
