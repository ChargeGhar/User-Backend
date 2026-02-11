"""
Core rental operations - start, cancel, extend, and active rental
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import rate_limit, log_api_call
from api.common.serializers import BaseResponseSerializer
from api.common.services.base import ServiceException
from api.user.rentals import serializers
from api.user.rentals.services import RentalService
from rest_framework.request import Request

core_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@core_router.register(r"rentals/start", name="rental-start")
@extend_schema(
    tags=["Rentals"],
    summary="Start Rental",
    description="Initiates a new power bank rental session",
    responses={201: BaseResponseSerializer}
)
class RentalStartView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalStartSerializer
    permission_classes = [IsAuthenticated]
    BUSINESS_BLOCKING_CODES = {
        'payment_required',
        'payment_method_required',
        'payment_mode_not_supported',
        'invalid_payment_mode',
        'invalid_wallet_points_split',
        'split_total_mismatch',
    }
    
    @extend_schema(
        summary="Start New Rental",
        description="Start a new power bank rental at specified station with selected package",
        request=serializers.RentalStartSerializer,
        responses={201: BaseResponseSerializer}
    )
    @rate_limit(max_requests=3, window_seconds=60)  # Max 3 rental attempts per minute
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Start new rental"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = RentalService()
        try:
            rental = service.start_rental(
                user=request.user,
                station_sn=serializer.validated_data['station_sn'],
                package_id=serializer.validated_data['package_id'],
                powerbank_sn=serializer.validated_data.get('powerbank_sn'),
                payment_method_id=serializer.validated_data.get('payment_method_id'),
                payment_mode=serializer.validated_data.get('payment_mode', 'wallet_points'),
                wallet_amount=serializer.validated_data.get('wallet_amount'),
                points_to_use=serializer.validated_data.get('points_to_use')
            )
        except ServiceException as exc:
            error_code = getattr(exc, 'default_code', 'service_error')
            error_context = getattr(exc, 'context', None) or None
            error_message = str(exc)

            if error_code in self.BUSINESS_BLOCKING_CODES:
                payload = {
                    'code': error_code,
                    'message': error_message
                }
                if error_context is not None:
                    payload['context'] = error_context
                return self.success_response(
                    data={'error': payload},
                    message=error_message,
                    status_code=status.HTTP_200_OK
                )

            return self.error_response(
                message=error_message,
                status_code=getattr(exc, 'status_code', status.HTTP_400_BAD_REQUEST),
                error_code=error_code,
                context=error_context
            )
        except Exception as exc:
            logger.error(f"Failed to start rental: {str(exc)}")
            return self.error_response(
                message="Failed to start rental",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code='internal_error'
            )

        response_serializer = serializers.RentalDetailSerializer(rental)
        return self.success_response(
            data=response_serializer.data,
            message="Rental started successfully",
            status_code=status.HTTP_201_CREATED
        )



@core_router.register(r"rentals/<str:rental_id>/cancel", name="rental-cancel")
@extend_schema(
    tags=["Rentals"],
    summary="Cancel Rental",
    description="Cancels an active rental",
    responses={200: BaseResponseSerializer}
)
class RentalCancelView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalCancelSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Cancel Active Rental",
        description="Cancel an active rental with optional reason",
        request=serializers.RentalCancelSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call(include_request_data=True)
    def post(self, request: Request, rental_id: str) -> Response:
        """Cancel rental"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = RentalService()
            result = service.cancel_rental(
                rental_id=rental_id,
                user=request.user,
                reason=serializer.validated_data.get('reason', '')
            )
            
            response_serializer = serializers.RentalDetailSerializer(result['rental'])
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Rental cancelled successfully",
            error_message="Failed to cancel rental"
        )



@core_router.register(r"rentals/<str:rental_id>/extend", name="rental-extend")
@extend_schema(
    tags=["Rentals"],
    summary="Extend Rental",
    description="Extends rental duration with additional package",
    responses={200: BaseResponseSerializer}
)
class RentalExtendView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalExtensionCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Extend Rental Duration",
        description="Extend rental duration by purchasing additional time package",
        request=serializers.RentalExtensionCreateSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request, rental_id: str) -> Response:
        """Extend rental"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = RentalService()
            extension = service.extend_rental(
                rental_id=rental_id,
                user=request.user,
                package_id=serializer.validated_data['package_id']
            )
            
            response_serializer = serializers.RentalExtensionSerializer(extension)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Rental extended successfully",
            error_message="Failed to extend rental"
        )



@core_router.register(r"rentals/active", name="rental-active")
@extend_schema(
    tags=["Rentals"],
    summary="Active Rental",
    description="Get user's current active rental",
    responses={200: BaseResponseSerializer}
)
class RentalActiveView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalDetailSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get Active Rental",
        description="Returns user's current active rental if any",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get active rental"""
        def operation():
            service = RentalService()
            rental = service.get_active_rental(request.user)
            if not rental:
                return None

            from decimal import Decimal
            from django.utils import timezone

            now = timezone.now()
            update_fields = []

            # Keep status in sync with realtime due time.
            if rental.status == 'ACTIVE' and rental.due_at and now > rental.due_at:
                rental.status = 'OVERDUE'
                update_fields.append('status')

            # Keep persisted overdue snapshot/payment state aligned for ongoing overdue rental.
            if rental.status == 'OVERDUE' and rental.ended_at is None:
                current_overdue = Decimal(str(rental.current_overdue_amount or Decimal('0'))).quantize(
                    Decimal('0.01')
                )
                if current_overdue != rental.overdue_amount:
                    rental.overdue_amount = current_overdue
                    update_fields.append('overdue_amount')
                if current_overdue > Decimal('0.00') and rental.payment_status != 'PENDING':
                    rental.payment_status = 'PENDING'
                    update_fields.append('payment_status')

            if update_fields:
                rental.save(update_fields=update_fields + ['updated_at'])

            serializer = self.get_serializer(rental)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Active rental retrieved",
            error_message="Failed to get active rental"
        )


@core_router.register(r"rentals/<str:rental_id>/swap", name="rental-swap")
@extend_schema(
    tags=["Rentals"],
    summary="Swap Powerbank",
    description="Swap current powerbank for a different one at same station",
    responses={200: BaseResponseSerializer}
)
class RentalSwapView(GenericAPIView, BaseAPIView):
    """
    Swap powerbank within active rental.
    
    Rules:
    - Must be within SWAPPING_MAX_TIME (5 min) from rental start
    - User must return current powerbank to same station first
    - Daily swap limit = available powerbanks at station
    - No payment involved
    """
    serializer_class = serializers.RentalSwapSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Swap Powerbank",
        description="Exchange current powerbank for a different one at the same station",
        request=serializers.RentalSwapSerializer,
        responses={200: BaseResponseSerializer}
    )
    @rate_limit(max_requests=5, window_seconds=60)  # Max 5 swap attempts per minute
    @log_api_call(include_request_data=True)
    def post(self, request: Request, rental_id: str) -> Response:
        """Swap powerbank"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = RentalService()
            rental = service.swap_powerbank(
                rental_id=rental_id,
                user=request.user,
                reason=serializer.validated_data.get('reason', 'OTHER'),
                description=serializer.validated_data.get('description', ''),
                powerbank_sn=serializer.validated_data.get('powerbank_sn')
            )
            
            response_serializer = serializers.RentalDetailSerializer(rental)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Powerbank swapped successfully",
            error_message="Failed to swap powerbank"
        )
