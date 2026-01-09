"""
User coupon operations - apply, validate, and personal history
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.promotions import serializers
from api.user.promotions.services import CouponService

coupon_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@coupon_router.register(r"promotions/coupons/apply", name="promotion-coupons-apply")
class CouponApplyView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.CouponApplySerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Promotions"],
        summary="Apply Coupon Code",
        description="Validate and apply coupon code to receive points. Includes built-in validation.",
        operation_id="apply_coupon_code",
        responses={200: serializers.CouponApplyResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Apply coupon code with validation - REAL-TIME (no caching for financial operations)"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            coupon_service = CouponService()
            
            # First validate the coupon
            validation_result = coupon_service.validate_coupon(
                coupon_code=serializer.validated_data['coupon_code'],
                user=request.user
            )
            
            # If validation fails, return validation details
            if not validation_result['can_use']:
                return {
                    'success': False,
                    'validation': validation_result,
                    'message': validation_result['message']
                }
            
            # Apply the coupon
            result = coupon_service.apply_coupon(
                coupon_code=serializer.validated_data['coupon_code'],
                user=request.user
            )
            
            # Include validation details in response
            result['validation'] = validation_result
            return result
        
        return self.handle_service_operation(
            operation,
            "Coupon applied successfully",
            "Failed to apply coupon"
        )



@coupon_router.register(r"promotions/coupons/my", name="promotion-coupons-my")
class MyCouponsView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.UserCouponHistorySerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Promotions"],
        summary="My Coupon History",
        description="Returns user's coupon usage history",
        operation_id="get_my_coupon_history",
        responses={200: serializers.MyCouponsResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user's coupon history - REAL-TIME (user-specific data)"""
        def operation():
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            coupon_service = CouponService()
            result = coupon_service.get_user_coupon_history(
                user=request.user,
                page=page,
                page_size=page_size
            )
            # Use MVP list serializer for performance
            serializer = serializers.UserCouponHistorySerializer(result['results'], many=True)
            
            return {
                'results': serializer.data,
                'pagination': result['pagination']
            }
        
        return self.handle_service_operation(
            operation,
            "Coupon history retrieved successfully",
            "Failed to retrieve coupon history"
        )

