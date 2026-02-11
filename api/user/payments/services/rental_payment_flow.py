from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from django.utils import timezone

from api.common.services.base import BaseService, ServiceException


class RentalPaymentFlowService(BaseService):
    """
    Shared helpers for rental start + rental due payment-mode flows.

    Centralizes:
    - payment option calculation
    - payment breakdown normalization (legacy + canonical keys)
    - payment-intent context payload for business-blocking responses
    """

    def calculate_payment_options(
        self,
        user,
        scenario: str,
        package_id: Optional[str] = None,
        rental_id: Optional[str] = None,
        amount: Optional[Decimal] = None,
        payment_mode: str = "wallet_points",
        wallet_amount: Optional[Decimal] = None,
        points_to_use: Optional[int] = None,
    ) -> Dict[str, Any]:
        from .payment_calculation import PaymentCalculationService

        calc_service = PaymentCalculationService()
        return calc_service.calculate_payment_options(
            user=user,
            scenario=scenario,
            package_id=package_id,
            rental_id=rental_id,
            amount=amount,
            payment_mode=payment_mode,
            wallet_amount=wallet_amount,
            points_to_use=points_to_use,
        )

    def normalize_breakdown(self, payment_breakdown: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        breakdown = payment_breakdown or {}

        points_to_use = int(
            breakdown.get("points_to_use", breakdown.get("points_used", 0)) or 0
        )
        points_amount = Decimal(str(breakdown.get("points_amount", Decimal("0"))))
        wallet_amount = Decimal(
            str(breakdown.get("wallet_amount", breakdown.get("wallet_used", Decimal("0"))))
        )

        if points_to_use < 0 or points_amount < 0 or wallet_amount < 0:
            raise ServiceException(
                detail="Payment breakdown values must be non-negative",
                code="invalid_payment_breakdown",
            )

        return {
            "points_to_use": points_to_use,
            "points_amount": points_amount.quantize(Decimal("0.01")),
            "wallet_amount": wallet_amount.quantize(Decimal("0.01")),
        }

    def normalize_breakdown_from_options(self, payment_options: Dict[str, Any]) -> Dict[str, Any]:
        breakdown = (payment_options or {}).get("payment_breakdown", {}) or {}
        return self.normalize_breakdown(breakdown)

    def create_topup_intent(
        self,
        user,
        payment_method_id: str,
        amount: Decimal,
        metadata: Dict[str, Any],
    ):
        from .payment_intent import PaymentIntentService

        intent_service = PaymentIntentService()
        intent = intent_service.create_topup_intent(
            user=user,
            amount=amount,
            payment_method_id=payment_method_id,
        )
        intent.intent_metadata.update(self.serialize_for_metadata(metadata or {}))
        intent.save(update_fields=["intent_metadata"])
        return intent

    def build_payment_required_context(
        self,
        intent,
        shortfall: Optional[Decimal] = None,
        payment_mode: Optional[str] = None,
        payment_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        gateway_result = intent.intent_metadata.get("gateway_result", {}) if intent.intent_metadata else {}
        context = {
            "intent_id": intent.intent_id,
            "amount": str(intent.amount),
            "currency": intent.currency,
            "gateway": intent.intent_metadata.get("gateway") if intent.intent_metadata else None,
            "gateway_url": intent.gateway_url,
            "redirect_url": gateway_result.get("redirect_url"),
            "redirect_method": gateway_result.get("redirect_method", "POST"),
            "form_fields": gateway_result.get("form_fields", {}),
            "payment_instructions": gateway_result.get("payment_instructions"),
            "expires_at": intent.expires_at.isoformat() if intent.expires_at else None,
            "status": intent.status,
            "shortfall": str(shortfall) if shortfall is not None else None,
        }

        if payment_mode:
            context["payment_mode"] = payment_mode

        if payment_options:
            context["wallet_shortfall"] = str(payment_options.get("wallet_shortfall", Decimal("0")))
            context["points_shortfall"] = payment_options.get("points_shortfall", 0)
            context["points_shortfall_amount"] = str(
                payment_options.get("points_shortfall_amount", Decimal("0"))
            )
            context["payment_breakdown"] = self.serialize_for_metadata(
                payment_options.get("payment_breakdown")
            )

        return context

    def serialize_for_metadata(self, value):
        """Convert Decimal recursively for JSON-safe metadata."""
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {key: self.serialize_for_metadata(val) for key, val in value.items()}
        if isinstance(value, list):
            return [self.serialize_for_metadata(item) for item in value]
        return value

    def calculate_required_due(self, rental) -> Decimal:
        """
        Calculate required due amount consistently for rental due settlement.

        Rules:
        - PREPAID: only overdue amount is collectible in due-settlement flow
        - POSTPAID: usage/base amount + overdue amount
        - For ongoing overdue rentals, use realtime overdue value
        """
        amount_paid = Decimal(str(rental.amount_paid or Decimal("0")))
        overdue_amount = Decimal(str(rental.overdue_amount or Decimal("0")))

        if (
            rental.ended_at is None
            and rental.started_at is not None
            and rental.due_at is not None
            and timezone.now() > rental.due_at
        ):
            overdue_amount = Decimal(str(rental.current_overdue_amount or Decimal("0")))

        amount_paid = amount_paid.quantize(Decimal("0.01"))
        overdue_amount = overdue_amount.quantize(Decimal("0.01"))

        if rental.package.payment_model == "PREPAID":
            return overdue_amount

        return (amount_paid + overdue_amount).quantize(Decimal("0.01"))
