"""
Support operations - issues, location tracking, and payments
"""

import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiParameter
from rest_framework import status, serializers as drf_serializers
from rest_framework.request import Request
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.rentals.serializers import core_serializers as serializers
from api.rentals.models import Rental
from api.rentals.services import RentalIssueService, RentalLocationService

support_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@support_router.register(r"rentals/<str:rental_id>/pay-due", name="rental-pay-due")
@extend_schema(
    tags=["Rentals"],
    summary="Settle Rental Dues",
    description="Settle outstanding rental dues",
    responses={200: BaseResponseSerializer}
)
class RentalPayDueView(GenericAPIView, BaseAPIView):
    serializer_class = drf_serializers.Serializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Settle Rental Dues",
        description="Settle outstanding rental dues using points and wallet combination",
        parameters=[
            OpenApiParameter(
                name="rental_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Rental ID with outstanding dues"
            )
        ],
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request, rental_id: str) -> Response:
        """Settle rental dues"""
        def operation():
            # Get rental
            rental = Rental.objects.get(id=rental_id, user=request.user)

            # Check if dues are already paid
            if rental.payment_status == 'PAID':
                from api.common.services.base import ServiceException
                raise ServiceException(
                    detail="Rental dues have already been settled",
                    code="dues_already_paid",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Calculate payment options first
            from api.payments.services import PaymentCalculationService
            calc_service = PaymentCalculationService()
            payment_options = calc_service.calculate_payment_options(
                user=request.user,
                scenario='post_payment',
                rental_id=rental_id
            )

            if not payment_options['is_sufficient']:
                from api.common.services.base import ServiceException
                raise ServiceException(
                    detail=f"Insufficient balance to pay dues. Need NPR {payment_options['shortfall']} more.",
                    code="insufficient_funds",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Process payment using rental payment service
            from api.payments.services import RentalPaymentService
            payment_service = RentalPaymentService()
            transaction = payment_service.pay_rental_due(
                user=request.user,
                rental=rental,
                payment_breakdown={
                    'points_to_use': payment_options['payment_breakdown']['points_used'],
                    'points_amount': payment_options['payment_breakdown']['points_amount'],
                    'wallet_amount': payment_options['payment_breakdown']['wallet_used'],
                    'total_amount': payment_options['total_amount']
                }
            )

            # Note: Rental status and overdue_amount are already updated by the payment service

            return {
                'transaction_id': transaction.transaction_id,
                'rental_id': str(rental.id),
                'amount_paid': float(payment_options['total_amount']),
                'payment_breakdown': {
                    'points_used': payment_options['payment_breakdown']['points_used'],
                    'points_amount': float(payment_options['payment_breakdown']['points_amount']),
                    'wallet_used': float(payment_options['payment_breakdown']['wallet_used'])
                },
                'payment_status': rental.payment_status,
                'account_unblocked': True
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Rental dues settled successfully",
            error_message="Failed to settle rental dues"
        )



@support_router.register(r"rentals/<str:rental_id>/issues", name="rental-issues")
@extend_schema(
    tags=["Rentals"],
    summary="Rental Issues",
    description="Report and manage rental issues",
    responses={201: BaseResponseSerializer}
)
class RentalIssueView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalIssueCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Report Rental Issue",
        description="Report an issue with current rental",
        request=serializers.RentalIssueCreateSerializer,
        responses={201: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request, rental_id: str) -> Response:
        """Report rental issue"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = RentalIssueService()
            issue = service.report_issue(
                rental_id=rental_id,
                user=request.user,
                validated_data=serializer.validated_data
            )
            
            response_serializer = serializers.RentalIssueSerializer(issue)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Issue reported successfully",
            error_message="Failed to report issue",
            success_status=status.HTTP_201_CREATED
        )

@support_router.register(r"rentals/<str:rental_id>/location", name="rental-location")
@extend_schema(
    tags=["Rentals"],
    summary="Rental Location",
    description="Update rental location tracking",
    responses={200: BaseResponseSerializer}
)
class RentalLocationView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalLocationUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Update Rental Location",
        description="Update GPS location for active rental tracking",
        request=serializers.RentalLocationUpdateSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request, rental_id: str) -> Response:
        """Update rental location"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = RentalLocationService()
            location = service.update_location(
                rental_id=rental_id,
                user=request.user,
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude'],
                accuracy=serializer.validated_data.get('accuracy', 10.0)
            )
            
            response_serializer = serializers.RentalLocationSerializer(location)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Location updated successfully",
            error_message="Failed to update location"
        )

