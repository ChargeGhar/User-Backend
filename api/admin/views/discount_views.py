"""
Admin Discount Views
"""
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.admin.serializers.discount_serializers import (
    CreateDiscountSerializer,
    UpdateDiscountSerializer,
    DiscountListSerializer,
    DiscountDetailSerializer,
    DiscountFiltersSerializer
)
from api.admin.services.admin_discount_service import AdminDiscountService
from api.user.auth.permissions import IsStaffPermission

discount_router = CustomViewRouter()


@discount_router.register(r"admin/discounts", name="admin-discounts")
@extend_schema(tags=["Admin - Discounts"])
class AdminDiscountListView(GenericAPIView, BaseAPIView):
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        summary="List Discounts",
        description="Get all station package discounts",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """List discounts"""
        def operation():
            filter_serializer = DiscountFiltersSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminDiscountService()
            discounts = service.get_discounts(filter_serializer.validated_data)
            
            return self.paginate_response(
                discounts, request, DiscountListSerializer
            )
        
        return self.handle_service_operation(
            operation,
            "Discounts retrieved successfully",
            "Failed to retrieve discounts"
        )
    
    @extend_schema(
        summary="Create Discount",
        description="Create new station package discount",
        request=CreateDiscountSerializer,
        responses={201: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create discount"""
        def operation():
            serializer = CreateDiscountSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminDiscountService()
            discount = service.create_discount(serializer.validated_data, request.user)
            
            return DiscountDetailSerializer(discount).data
        
        return self.handle_service_operation(
            operation,
            "Discount created successfully",
            "Failed to create discount"
        )


@discount_router.register(r"admin/discounts/<uuid:discount_id>", name="admin-discount-detail")
@extend_schema(tags=["Admin - Discounts"])
class AdminDiscountDetailView(GenericAPIView, BaseAPIView):
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        summary="Get Discount",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request, discount_id: str) -> Response:
        """Get discount details"""
        def operation():
            service = AdminDiscountService()
            discount = service.get_discount(discount_id)
            return DiscountDetailSerializer(discount).data
        
        return self.handle_service_operation(
            operation,
            "Discount retrieved successfully",
            "Failed to retrieve discount"
        )
    
    @extend_schema(
        summary="Update Discount",
        request=UpdateDiscountSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, discount_id: str) -> Response:
        """Update discount"""
        def operation():
            serializer = UpdateDiscountSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminDiscountService()
            discount = service.update_discount(discount_id, serializer.validated_data)
            
            return DiscountDetailSerializer(discount).data
        
        return self.handle_service_operation(
            operation,
            "Discount updated successfully",
            "Failed to update discount"
        )
    
    @extend_schema(summary="Delete Discount")
    @log_api_call()
    def delete(self, request: Request, discount_id: str) -> Response:
        """Delete discount"""
        def operation():
            service = AdminDiscountService()
            service.delete_discount(discount_id)
            return {'message': 'Discount deleted successfully'}
        
        return self.handle_service_operation(
            operation,
            "Discount deleted successfully",
            "Failed to delete discount"
        )
