"""
Support operations - due, issues, location tracking, and payments.
"""

import logging
from decimal import Decimal

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.common.services.base import ServiceException
from api.user.payments.services import RentalPaymentFlowService  # backward-compatible patch target for tests
from api.user.rentals import serializers
from api.user.rentals.models import Rental
from api.user.rentals.services import (
    RentalDuePaymentService,
    RentalIssueService,
    RentalLocationService,
)

support_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@support_router.register(r"rentals/<str:rental_id>/pay-due", name="rental-pay-due")
@extend_schema(
    tags=["Rentals"],
    summary="Settle Rental Dues",
    description="Settle outstanding rental dues using wallet, points, wallet+points, or direct payment",
    responses={200: BaseResponseSerializer},
)
class RentalPayDueView(GenericAPIView, BaseAPIView):
    """View for settling rental dues with a consistent payment-mode flow."""

    serializer_class = serializers.RentalPayDueSerializer
    permission_classes = [IsAuthenticated]

    BUSINESS_BLOCKING_CODES = {
        "payment_required",
        "payment_method_required",
        "invalid_payment_mode",
        "invalid_wallet_points_split",
        "split_total_mismatch",
    }

    @extend_schema(
        summary="Settle Rental Dues",
        description=(
            "Settle outstanding rental dues.\n\n"
            "Payment modes:\n"
            "- wallet\n"
            "- points\n"
            "- wallet_points\n"
            "- direct\n\n"
            "If balance is insufficient, returns business-blocking payload."
        ),
        request=serializers.RentalPayDueSerializer,
        parameters=[
            OpenApiParameter(
                name="rental_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Rental ID with outstanding dues",
            )
        ],
        responses={200: BaseResponseSerializer, 402: BaseResponseSerializer},
    )
    @log_api_call()
    def post(self, request: Request, rental_id: str) -> Response:
        """
        Settle rental dues.

        Flow:
        1. Validate request.
        2. Validate rental and required due.
        3. Delegate payment decision + processing to service.
        4. Return success or wrapped business-blocking error.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_mode = serializer.validated_data.get("payment_mode", "wallet_points")
        wallet_amount = serializer.validated_data.get("wallet_amount")
        points_to_use = serializer.validated_data.get("points_to_use")
        payment_method_id = serializer.validated_data.get("payment_method_id")

        try:
            rental = Rental.objects.get(id=rental_id, user=request.user)
            flow_service = RentalPaymentFlowService()

            if (
                rental.started_at is None
                and rental.payment_status == "PAID"
                and (
                    rental.rental_metadata.get("popup_message")
                    or rental.rental_metadata.get("popup_failed")
                )
            ):
                raise ServiceException(
                    detail="Rental was not started due to popup timeout/failure. Due settlement is not applicable.",
                    code="rental_not_started",
                )

            required_due = flow_service.calculate_required_due(rental)

            if required_due <= 0:
                if rental.started_at is not None and rental.payment_status != "PAID":
                    rental.payment_status = "PAID"
                    rental.save(update_fields=["payment_status", "updated_at"])
                raise ServiceException(
                    detail="Rental dues have already been settled",
                    code="dues_already_paid",
                )

            # Keep persisted status aligned when due is dynamic and rental is still running overdue.
            if rental.status == "OVERDUE" and rental.ended_at is None:
                current_overdue = Decimal(str(rental.current_overdue_amount or Decimal("0"))).quantize(
                    Decimal("0.01")
                )
                update_fields = []
                if current_overdue != rental.overdue_amount:
                    rental.overdue_amount = current_overdue
                    update_fields.append("overdue_amount")
                if rental.payment_status != "PENDING":
                    rental.payment_status = "PENDING"
                    update_fields.append("payment_status")
                if update_fields:
                    rental.save(update_fields=update_fields + ["updated_at"])

            payment_service = RentalDuePaymentService()
            result = payment_service.pay_rental_due(
                user=request.user,
                rental=rental,
                payment_mode=payment_mode,
                wallet_amount=wallet_amount,
                points_to_use=points_to_use,
                payment_method_id=str(payment_method_id) if payment_method_id else None,
            )

            return self.success_response(
                data=result,
                message="Rental dues settled successfully",
                status_code=status.HTTP_200_OK,
            )

        except ServiceException as exc:
            error_code = getattr(exc, "default_code", "service_error")
            error_context = getattr(exc, "context", None)
            error_message = str(exc)

            if error_code in self.BUSINESS_BLOCKING_CODES:
                payload = {"code": error_code, "message": error_message}
                if error_context is not None:
                    payload["context"] = error_context
                return self.success_response(
                    data={"error": payload},
                    message=error_message,
                    status_code=status.HTTP_200_OK,
                )

            return self.error_response(
                message=error_message,
                status_code=getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST),
                error_code=error_code,
                context=error_context,
            )

        except Rental.DoesNotExist:
            return self.error_response(
                message="Rental not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="rental_not_found",
            )

        except Exception as exc:
            logger.exception(f"Failed to settle rental dues: {str(exc)}")
            return self.error_response(
                message="Failed to settle rental dues",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="internal_error",
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
        responses={201: BaseResponseSerializer},
    )
    @log_api_call()
    def post(self, request: Request, rental_id: str) -> Response:
        """Report rental issue."""

        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            service = RentalIssueService()
            issue = service.report_issue(
                rental_id=rental_id,
                user=request.user,
                validated_data=serializer.validated_data,
            )

            response_serializer = serializers.RentalIssueSerializer(issue)
            return response_serializer.data

        return self.handle_service_operation(
            operation,
            success_message="Issue reported successfully",
            error_message="Failed to report issue",
            success_status=status.HTTP_201_CREATED,
        )


@support_router.register(r"rentals/<str:rental_id>/location", name="rental-location")
@extend_schema(
    tags=["Rentals"],
    summary="Rental Location",
    description="Update rental location tracking",
    responses={200: BaseResponseSerializer},
)
class RentalLocationView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalLocationUpdateSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update Rental Location",
        description="Update GPS location for active rental tracking",
        request=serializers.RentalLocationUpdateSerializer,
        responses={200: BaseResponseSerializer},
    )
    @log_api_call()
    def post(self, request: Request, rental_id: str) -> Response:
        """Update rental location."""

        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            service = RentalLocationService()
            location = service.update_location(
                rental_id=rental_id,
                user=request.user,
                latitude=serializer.validated_data["latitude"],
                longitude=serializer.validated_data["longitude"],
                accuracy=serializer.validated_data.get("accuracy", 10.0),
            )

            response_serializer = serializers.RentalLocationSerializer(location)
            return response_serializer.data

        return self.handle_service_operation(
            operation,
            success_message="Location updated successfully",
            error_message="Failed to update location",
        )
