"""
Admin KYC management views
============================================================

This module contains views for admin KYC verification operations.

Created: 2025-11-06
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission
from api.admin import serializers
from api.admin.services import AdminUserService

kyc_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@kyc_router.register(r"admin/kyc/submissions", name="admin-kyc-list")
@extend_schema(
    tags=["Admin - KYC"],
    summary="KYC Submissions Management",
    description="Get all KYC submissions with filtering and pagination",
    responses={200: BaseResponseSerializer}
)
class AdminKYCListView(GenericAPIView, BaseAPIView):
    """Admin view for managing KYC submissions"""
    serializer_class = serializers.AdminKYCListSerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get list of KYC submissions with filters"""
        def operation():
            serializer = self.get_serializer(data=request.query_params)
            serializer.is_valid(raise_exception=True)
            
            admin_service = AdminUserService()
            result = admin_service.get_kyc_submissions(serializer.validated_data)
            
            # Serialize KYC data
            kyc_serializer = serializers.AdminKYCSerializer(result['results'], many=True)
            
            return {
                'kyc_submissions': kyc_serializer.data,
                'pagination': result['pagination']
            }
        
        return self.handle_service_operation(
            operation,
            success_message="KYC submissions retrieved successfully",
            error_message="Failed to retrieve KYC submissions"
        )


@kyc_router.register(r"admin/kyc/submissions/<uuid:kyc_id>", name="admin-kyc-status-update")
@extend_schema(
    tags=["Admin - KYC"],
    summary="Update KYC Status",
    description="Approve or reject a KYC submission",
    responses={200: BaseResponseSerializer}
)
class AdminKYCStatusUpdateView(GenericAPIView, BaseAPIView):
    """Admin view for updating KYC submission status"""
    serializer_class = serializers.UpdateKYCStatusSerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def patch(self, request: Request, kyc_id: str) -> Response:
        """Update KYC status (approve/reject)"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            admin_service = AdminUserService()
            result = admin_service.update_kyc_status(
                kyc_id=kyc_id,
                status=serializer.validated_data['status'],
                rejection_reason=serializer.validated_data.get('rejection_reason', ''),
                admin_user=request.user
            )
            
            return result
        
        return self.handle_service_operation(
            operation,
            success_message="KYC status updated successfully",
            error_message="Failed to update KYC status"
        )
