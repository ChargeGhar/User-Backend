"""
Admin coupon management views
============================================================

This module contains views for admin coupon management operations.

Created: 2025-11-05
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers
from api.admin.services import AdminCouponService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission
from api.user.promotions.serializers import CouponSerializer, CouponUsageSerializer

coupon_router = CustomViewRouter()
logger = logging.getLogger(__name__)


# ============================================================
# Coupon Management Views
# ============================================================
@coupon_router.register(r"admin/coupons", name="admin-coupons")
@extend_schema(
    tags=["Admin - Coupons"],
    summary="Coupon Management",
    description="Manage promotional coupons (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminCouponView(GenericAPIView, BaseAPIView):
    """Admin coupon management"""
    serializer_class = serializers.CouponListSerializer
    permission_classes = [IsStaffPermission]

    @extend_schema(
        summary="List Coupons",
        description="Get paginated list of coupons with filters"
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get coupon list with filters"""
        def operation():
            filter_serializer = serializers.CouponListSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)

            service = AdminCouponService()
            paginated_result = service.get_coupons(filter_serializer.validated_data)

            serializer = CouponSerializer(paginated_result['results'], many=True)
            paginated_result['results'] = serializer.data
            
            return paginated_result
        
        return self.handle_service_operation(
            operation,
            "Coupons retrieved successfully",
            "Failed to retrieve coupons"
        )

    @extend_schema(
        summary="Create Coupon",
        description="Create a new promotional coupon",
        request=serializers.CreateCouponSerializer
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create coupon"""
        def operation():
            create_serializer = serializers.CreateCouponSerializer(data=request.data)
            create_serializer.is_valid(raise_exception=True)

            service = AdminCouponService()
            coupon = service.create_coupon(create_serializer.validated_data, request.user, request=request)

            serializer = CouponSerializer(coupon)
            return serializer.data
        
        result = self.handle_service_operation(
            operation,
            "Coupon created successfully",
            "Failed to create coupon"
        )
        result.status_code = status.HTTP_201_CREATED
        return result


@coupon_router.register(r"admin/coupons/bulk", name="admin-coupons-bulk")
@extend_schema(
    tags=["Admin - Coupons"],
    summary="Bulk Create Coupons",
    description="Create multiple coupons at once",
    request=serializers.BulkCreateCouponSerializer,
    responses={201: BaseResponseSerializer}
)
class AdminCouponBulkView(GenericAPIView, BaseAPIView):
    """Bulk create coupons"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Bulk create coupons"""
        def operation():
            bulk_serializer = serializers.BulkCreateCouponSerializer(data=request.data)
            bulk_serializer.is_valid(raise_exception=True)

            service = AdminCouponService()
            coupons = service.bulk_create_coupons(bulk_serializer.validated_data, request.user, request=request)

            serializer = CouponSerializer(coupons, many=True)
            
            return {
                'count': len(coupons),
                'codes': [c.code for c in coupons],
                'coupons': serializer.data,
                'message': f'Successfully created {len(coupons)} coupons'
            }
        
        result = self.handle_service_operation(
            operation,
            "Coupons created successfully",
            "Failed to create coupons"
        )
        result.status_code = status.HTTP_201_CREATED
        return result


@coupon_router.register(r"admin/coupons/<str:coupon_code>", name="admin-coupon-detail")
@extend_schema(
    tags=["Admin - Coupons"],
    summary="Coupon Details",
    description="Get, update, or delete a specific coupon",
    responses={200: BaseResponseSerializer}
)
class AdminCouponDetailView(GenericAPIView, BaseAPIView):
    """Admin coupon detail operations"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        summary="Get Coupon Details",
        description="Get details of a specific coupon including usage stats"
    )
    @log_api_call()
    def get(self, request: Request, coupon_code: str) -> Response:
        """Get coupon details"""
        def operation():
            service = AdminCouponService()
            coupon_detail = service.get_coupon_detail(coupon_code)

            serializer = CouponSerializer(coupon_detail['coupon'])
            data = serializer.data
            data['usage_stats'] = coupon_detail['usage_stats']
            
            return data
        
        return self.handle_service_operation(
            operation,
            "Coupon details retrieved successfully",
            "Failed to retrieve coupon details"
        )
    
    @extend_schema(
        summary="Update Coupon",
        description="Update coupon status and/or public visibility",
        request=serializers.UpdateCouponStatusSerializer
    )
    @log_api_call()
    def patch(self, request: Request, coupon_code: str) -> Response:
        """Update coupon status/visibility"""
        def operation():
            status_serializer = serializers.UpdateCouponStatusSerializer(data=request.data)
            status_serializer.is_valid(raise_exception=True)

            service = AdminCouponService()
            coupon = service.update_coupon(coupon_code, status_serializer.validated_data, request.user, request=request)

            serializer = CouponSerializer(coupon)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Coupon status updated successfully",
            "Failed to update coupon status"
        )
    
    @extend_schema(
        summary="Delete Coupon",
        description="Delete a coupon (soft delete)"
    )
    @log_api_call()
    def delete(self, request: Request, coupon_code: str) -> Response:
        """Delete coupon"""
        def operation():
            service = AdminCouponService()
            service.soft_delete_coupon(coupon_code, request.user, request=request)

            return {'message': f'Coupon {coupon_code} deleted successfully'}
        
        return self.handle_service_operation(
            operation,
            "Coupon deleted successfully",
            "Failed to delete coupon"
        )


@coupon_router.register(r"admin/coupons/<str:coupon_code>/usages", name="admin-coupon-usages")
@extend_schema(
    tags=["Admin - Coupons"],
    summary="Coupon Usage History",
    description="Get usage history for a specific coupon",
    responses={200: BaseResponseSerializer}
)
class AdminCouponUsageView(GenericAPIView, BaseAPIView):
    """Coupon usage history"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request, coupon_code: str) -> Response:
        """Get coupon usage history"""
        def operation():
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))

            service = AdminCouponService()
            paginated = service.get_coupon_usages(coupon_code, page=page, page_size=page_size)

            serializer = CouponUsageSerializer(paginated['results'], many=True)
            paginated['results'] = serializer.data
            
            return paginated
        
        return self.handle_service_operation(
            operation,
            "Coupon usage history retrieved successfully",
            "Failed to retrieve coupon usage history"
        )
