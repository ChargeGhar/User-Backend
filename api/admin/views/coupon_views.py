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
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.promotions.services import CouponService
from api.user.auth.permissions import IsStaffPermission

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
            # Parse filters
            filters = {
                'status': request.query_params.get('status'),
                'search': request.query_params.get('search'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': int(request.query_params.get('page', 1)),
                'page_size': int(request.query_params.get('page_size', 20))
            }
            
            service = CouponService()
            paginated_result = service.get_coupons_list(filters)
            
            # Serialize the coupons
            from api.user.promotions.serializers import CouponSerializer
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
            
            service = CouponService()
            coupon = service.create_coupon(
                code=create_serializer.validated_data['code'],
                name=create_serializer.validated_data['name'],
                points_value=create_serializer.validated_data['points_value'],
                max_uses_per_user=create_serializer.validated_data['max_uses_per_user'],
                valid_from=create_serializer.validated_data['valid_from'],
                valid_until=create_serializer.validated_data['valid_until'],
                admin_user=request.user
            )
            
            from api.user.promotions.serializers import CouponSerializer
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
            
            service = CouponService()
            coupons = service.bulk_create_coupons(
                name_prefix=bulk_serializer.validated_data['name_prefix'],
                points_value=bulk_serializer.validated_data['points_value'],
                max_uses_per_user=bulk_serializer.validated_data['max_uses_per_user'],
                valid_from=bulk_serializer.validated_data['valid_from'],
                valid_until=bulk_serializer.validated_data['valid_until'],
                quantity=bulk_serializer.validated_data['quantity'],
                code_length=bulk_serializer.validated_data.get('code_length', 8),
                admin_user=request.user
            )
            
            # Serialize the created coupons
            from api.user.promotions.serializers import CouponSerializer
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
            from api.user.promotions.models import Coupon, CouponUsage
            from api.user.promotions.serializers import CouponSerializer
            
            coupon = Coupon.objects.get(code=coupon_code.upper())
            
            # Get usage statistics
            total_uses = CouponUsage.objects.filter(coupon=coupon).count()
            unique_users = CouponUsage.objects.filter(coupon=coupon).values('user').distinct().count()
            total_points_awarded = sum(
                usage.points_awarded 
                for usage in CouponUsage.objects.filter(coupon=coupon)
            )
            
            serializer = CouponSerializer(coupon)
            data = serializer.data
            data['usage_stats'] = {
                'total_uses': total_uses,
                'unique_users': unique_users,
                'total_points_awarded': total_points_awarded
            }
            
            return data
        
        return self.handle_service_operation(
            operation,
            "Coupon details retrieved successfully",
            "Failed to retrieve coupon details"
        )
    
    @extend_schema(
        summary="Update Coupon Status",
        description="Update coupon status (activate/deactivate)",
        request=serializers.UpdateCouponStatusSerializer
    )
    @log_api_call()
    def patch(self, request: Request, coupon_code: str) -> Response:
        """Update coupon status"""
        def operation():
            from api.user.promotions.models import Coupon
            from api.user.promotions.serializers import CouponSerializer
            
            status_serializer = serializers.UpdateCouponStatusSerializer(data=request.data)
            status_serializer.is_valid(raise_exception=True)
            
            coupon = Coupon.objects.get(code=coupon_code.upper())
            old_status = coupon.status
            new_status = status_serializer.validated_data['status']
            
            coupon.status = new_status
            coupon.save(update_fields=['status', 'updated_at'])
            
            # Log admin action
            from api.admin.models import AdminActionLog
            AdminActionLog.objects.create(
                admin_user=request.user,
                action_type='UPDATE_COUPON_STATUS',
                target_model='Coupon',
                target_id=str(coupon.id),
                changes={'old_status': old_status, 'new_status': new_status},
                description=f"Updated coupon {coupon_code} status from {old_status} to {new_status}",
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
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
            from api.user.promotions.models import Coupon
            
            coupon = Coupon.objects.get(code=coupon_code.upper())
            coupon_id = str(coupon.id)
            coupon.name
            
            # Soft delete by setting status to inactive
            coupon.status = Coupon.StatusChoices.INACTIVE
            coupon.save(update_fields=['status', 'updated_at'])
            
            # Log admin action
            from api.admin.models import AdminActionLog
            AdminActionLog.objects.create(
                admin_user=request.user,
                action_type='DELETE_COUPON',
                target_model='Coupon',
                target_id=coupon_id,
                changes={'status': 'inactive'},
                description=f"Deleted coupon: {coupon_code}",
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
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
            from api.user.promotions.models import Coupon, CouponUsage
            from api.user.promotions.serializers import CouponUsageSerializer
            from api.common.utils.helpers import paginate_queryset
            
            coupon = Coupon.objects.get(code=coupon_code.upper())
            
            queryset = CouponUsage.objects.filter(coupon=coupon).select_related('user')
            queryset = queryset.order_by('-used_at')
            
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            paginated = paginate_queryset(queryset, page, page_size)
            
            # Serialize the results
            serializer = CouponUsageSerializer(paginated['results'], many=True)
            paginated['results'] = serializer.data
            
            return paginated
        
        return self.handle_service_operation(
            operation,
            "Coupon usage history retrieved successfully",
            "Failed to retrieve coupon usage history"
        )
