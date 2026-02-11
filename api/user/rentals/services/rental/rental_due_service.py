"""
Rental due payment service.

This service keeps the same payment-mode lifecycle as rental start:
- wallet: use wallet if sufficient, otherwise gateway intent
- points: use points if sufficient, otherwise gateway intent
- wallet_points: use split if sufficient, otherwise gateway intent
- direct: always gateway intent
"""

from decimal import Decimal
from typing import Any, Dict, Optional

from api.common.services.base import BaseService, ServiceException
from api.user.payments.services import RentalPaymentFlowService, RentalPaymentService
from api.user.rentals.models import Rental


class RentalDuePaymentService(BaseService):
    """Orchestrates due settlement using payment-mode rules."""

    def pay_rental_due(
        self,
        user,
        rental: Rental,
        payment_mode: str = "wallet_points",
        wallet_amount: Optional[Decimal] = None,
        points_to_use: Optional[int] = None,
        payment_method_id: Optional[str] = None,
        required_due_override: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Settle outstanding rental due.

        Returns transaction details if paid, or raises ServiceException for
        blocking conditions such as payment_required/payment_method_required.
        """
        try:
            flow_service = RentalPaymentFlowService()
            selected_mode = payment_mode or "wallet_points"

            if required_due_override is not None:
                required_due = Decimal(str(required_due_override)).quantize(Decimal("0.01"))
            else:
                required_due = flow_service.calculate_required_due(rental)
            if required_due <= 0:
                raise ServiceException(
                    detail="No due amount pending for this rental",
                    code="no_due_amount",
                )

            self._validate_payment_or_raise_gateway(
                user=user,
                rental=rental,
                required_due=required_due,
                payment_mode=selected_mode,
                payment_method_id=payment_method_id,
                wallet_amount=wallet_amount,
                points_to_use=points_to_use,
                flow_service=flow_service,
            )

            payment_options = flow_service.calculate_payment_options(
                user=user,
                scenario="post_payment",
                rental_id=str(rental.id),
                amount=required_due,
                payment_mode=selected_mode,
                wallet_amount=wallet_amount,
                points_to_use=points_to_use,
            )
            normalized_breakdown = flow_service.normalize_breakdown_from_options(payment_options)

            payment_service = RentalPaymentService()
            transaction = payment_service.pay_rental_due(
                user=user,
                rental=rental,
                payment_breakdown=normalized_breakdown,
                is_powerbank_returned=bool(rental.ended_at),
                required_due_override=required_due,
            )

            return {
                "transaction_id": transaction.transaction_id,
                "rental_id": str(rental.id),
                "rental_code": rental.rental_code,
                "amount_paid": float(required_due),
                "payment_breakdown": {
                    "points_used": normalized_breakdown["points_to_use"],
                    "wallet_used": float(normalized_breakdown["wallet_amount"]),
                    "points_to_use": normalized_breakdown["points_to_use"],
                    "points_amount": float(normalized_breakdown["points_amount"]),
                    "wallet_amount": float(normalized_breakdown["wallet_amount"]),
                },
                "payment_status": rental.payment_status,
                "account_unblocked": True,
            }
        except Exception as exc:
            if isinstance(exc, ServiceException):
                raise
            self.handle_service_error(exc, "Failed to pay rental due")

    def _validate_payment_or_raise_gateway(
        self,
        user,
        rental: Rental,
        required_due: Decimal,
        payment_mode: str,
        payment_method_id: Optional[str],
        wallet_amount: Optional[Decimal],
        points_to_use: Optional[int],
        flow_service: RentalPaymentFlowService,
    ) -> None:
        """Check payment sufficiency and raise payment_required when needed."""
        if payment_mode == "direct":
            topup_amount = required_due.quantize(Decimal("0.01"))
            self._raise_payment_gateway_required(
                flow_service=flow_service,
                user=user,
                rental=rental,
                topup_amount=topup_amount,
                required_due=required_due,
                payment_mode=payment_mode,
                payment_method_id=payment_method_id,
                resume_mode="wallet",
                resume_wallet=None,
                resume_points=None,
            )

        payment_options = flow_service.calculate_payment_options(
            user=user,
            scenario="post_payment",
            rental_id=str(rental.id),
            amount=required_due,
            payment_mode=payment_mode,
            wallet_amount=wallet_amount,
            points_to_use=points_to_use,
        )

        if payment_options["is_sufficient"]:
            return

        topup_amount = Decimal(
            str(
                payment_options.get("topup_amount_required")
                or payment_options.get("shortfall")
                or required_due
            )
        )
        resume_mode, resume_wallet, resume_points = self._get_resume_preferences(
            payment_mode, wallet_amount, points_to_use, payment_options
        )
        self._raise_payment_gateway_required(
            flow_service=flow_service,
            user=user,
            rental=rental,
            topup_amount=topup_amount,
            required_due=required_due,
            payment_mode=payment_mode,
            payment_method_id=payment_method_id,
            resume_mode=resume_mode,
            resume_wallet=resume_wallet,
            resume_points=resume_points,
            payment_options=payment_options,
        )

    def _raise_payment_gateway_required(
        self,
        flow_service: RentalPaymentFlowService,
        user,
        rental: Rental,
        topup_amount: Decimal,
        required_due: Decimal,
        payment_mode: str,
        payment_method_id: Optional[str],
        resume_mode: str,
        resume_wallet: Optional[Decimal],
        resume_points: Optional[int],
        payment_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create intent and raise payment_required exception."""
        if not payment_method_id:
            raise ServiceException(
                detail="Payment method is required when balance is insufficient",
                code="payment_method_required",
                context={
                    "payment_mode": payment_mode,
                    "shortfall": str(topup_amount),
                    "required_due": str(required_due),
                },
            )

        gateway_topup_amount = flow_service.resolve_gateway_topup_amount(
            payment_method_id=payment_method_id,
            requested_amount=topup_amount,
        )

        metadata = {
            "flow": "RENTAL_DUE",
            "rental_id": str(rental.id),
            "rental_code": rental.rental_code,
            "required_due": str(required_due),
            "payment_mode_requested": payment_mode,
            "payment_mode": resume_mode,
            "wallet_amount": str(resume_wallet) if resume_wallet is not None else None,
            "points_to_use": resume_points,
            "topup_amount_required": str(gateway_topup_amount),
            "shortfall": str(topup_amount),
        }
        if payment_options:
            metadata["payment_breakdown"] = flow_service.serialize_for_metadata(
                payment_options.get("payment_breakdown")
            )
            metadata["shortfall"] = str(payment_options.get("shortfall", topup_amount))

        intent = flow_service.create_topup_intent(
            user=user,
            payment_method_id=payment_method_id,
            amount=gateway_topup_amount,
            metadata=metadata,
        )

        raise ServiceException(
            detail="Payment required to settle rental dues",
            code="payment_required",
            status_code=402,
            context=flow_service.build_payment_required_context(
                intent=intent,
                shortfall=topup_amount if not payment_options else payment_options.get("shortfall"),
                payment_mode=payment_mode,
                payment_options=payment_options,
            ),
        )

    def _get_resume_preferences(
        self,
        selected_mode: str,
        wallet_amount: Optional[Decimal],
        points_to_use: Optional[int],
        payment_options: Dict[str, Any],
    ) -> tuple[str, Optional[Decimal], Optional[int]]:
        """Build deterministic resume preferences after gateway top-up."""
        resume_mode = self._get_resume_mode(selected_mode)
        resume_wallet = wallet_amount
        resume_points = points_to_use

        has_requested_split = wallet_amount is not None and points_to_use is not None
        if selected_mode == "wallet_points" and has_requested_split:
            points_shortfall = int(payment_options.get("points_shortfall", 0) or 0)
            if points_shortfall > 0:
                resume_wallet = None
                resume_points = None

        return resume_mode, resume_wallet, resume_points

    def _get_resume_mode(self, payment_mode: str) -> str:
        """Determine mode to use when resuming due settlement after top-up."""
        if payment_mode == "direct":
            return "wallet"
        if payment_mode == "points":
            return "wallet_points"
        return payment_mode
