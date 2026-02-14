from __future__ import annotations

from typing import Dict, Any, Optional
from decimal import Decimal
from django.db import transaction

from api.common.services.base import BaseService, ServiceException
from api.common.utils.helpers import generate_transaction_id
from api.user.payments.repositories.transaction_repository import TransactionRepository
from api.user.payments.services.wallet import WalletService
from api.user.payments.services.rental_payment_flow import RentalPaymentFlowService

class RentalPaymentService(BaseService):
    """Service for rental payments"""

    def _normalize_payment_breakdown(self, payment_breakdown: Dict[str, Any]) -> Dict[str, Any]:
        return RentalPaymentFlowService().normalize_breakdown(payment_breakdown)

    def _build_payment_gateway_response(
        self,
        points_to_use: int,
        points_amount: Decimal,
        wallet_amount: Decimal,
    ) -> Dict[str, Any]:
        total_amount = (points_amount + wallet_amount).quantize(Decimal('0.01'))
        return {
            'points_used': int(points_to_use or 0),
            'points_amount': str(points_amount.quantize(Decimal('0.01'))),
            'wallet_amount': str(wallet_amount.quantize(Decimal('0.01'))),
            'total_amount': str(total_amount),
        }

    @transaction.atomic
    def process_rental_payment(self, user, rental, payment_breakdown: Dict[str, Any]) -> Transaction:
        """Process payment for rental"""
        try:
            normalized = self._normalize_payment_breakdown(payment_breakdown)
            points_amount = normalized['points_amount']
            wallet_amount = normalized['wallet_amount']
            points_to_use = normalized['points_to_use']

            # Calculate total amount
            total_amount = points_amount + wallet_amount

            # Create transaction record
            transaction_obj = TransactionRepository.create(
                user=user,
                transaction_id=generate_transaction_id(),
                transaction_type='RENTAL',
                amount=total_amount,
                status='SUCCESS',
                payment_method_type='COMBINATION' if points_to_use > 0 and wallet_amount > 0 else 'POINTS' if points_to_use > 0 else 'WALLET',
                related_rental=rental,
                gateway_response=self._build_payment_gateway_response(
                    points_to_use=points_to_use,
                    points_amount=points_amount,
                    wallet_amount=wallet_amount,
                ),
            )

            # Get rental code or use a placeholder if rental is None
            rental_description = f"Payment for rental {rental.rental_code}" if rental else "Payment for new rental"

            # Deduct points if used
            if points_to_use > 0:
                from api.user.points.services import deduct_points
                points_kwargs = {'related_rental': rental} if rental else {}
                deduct_points(
                    user,
                    points_to_use,
                    'RENTAL_PAYMENT',
                    rental_description,
                    async_send=False,  # Immediate for payment processing
                    **points_kwargs
                )

            # Deduct wallet balance if used
            if wallet_amount > 0:
                wallet_service = WalletService()
                wallet_service.deduct_balance(
                    user,
                    wallet_amount,
                    rental_description,
                    transaction_obj
                )

            rental_code = rental.rental_code if rental else "new_rental"
            self.log_info(f"Rental payment processed: {rental_code} for user {user.username}")
            
            # Note: Revenue distribution for PREPAID is triggered from start.py 
            # after rental activation (popup success), not here
            # This is because rental might fail at popup stage and need refund
            
            return transaction_obj

        except Exception as e:
            self.handle_service_error(e, "Failed to process rental payment")

    @transaction.atomic
    def pay_rental_due(
        self,
        user,
        rental,
        payment_breakdown: Dict[str, Any],
        is_powerbank_returned: bool = True,
        required_due_override: Optional[Decimal] = None,
    ):
        """
        Pay outstanding rental dues.

        Args:
            user: The user making payment
            rental: The rental with dues
            payment_breakdown: Payment amounts breakdown
            is_powerbank_returned: Whether powerbank has been returned

        Returns:
            Transaction object
        """
        try:
            normalized = self._normalize_payment_breakdown(payment_breakdown)
            points_amount = normalized['points_amount']
            wallet_amount = normalized['wallet_amount']
            points_to_use = normalized['points_to_use']

            total_amount = (points_amount + wallet_amount).quantize(Decimal('0.01'))
            if required_due_override is not None:
                required_due = Decimal(str(required_due_override)).quantize(Decimal('0.01'))
            else:
                required_due = RentalPaymentFlowService().calculate_required_due(rental)

            if required_due <= 0:
                raise ServiceException(
                    detail="No due amount pending for this rental",
                    code="no_due_amount"
                )

            if total_amount != required_due:
                raise ServiceException(
                    detail=f"Payment breakdown amount mismatch. Expected NPR {required_due}, got NPR {total_amount}.",
                    code="payment_amount_mismatch",
                    context={
                        'required_due': str(required_due),
                        'provided_total': str(total_amount),
                        'points_amount': str(points_amount),
                        'wallet_amount': str(wallet_amount),
                        'points_to_use': points_to_use,
                    }
                )

            payment_type = (
                'COMBINATION' if points_to_use > 0 and wallet_amount > 0
                else 'POINTS' if points_to_use > 0
                else 'WALLET'
            )

            transaction_obj = TransactionRepository.create(
                user=user,
                transaction_id=generate_transaction_id(),
                transaction_type='RENTAL_DUE',
                amount=total_amount,
                status='SUCCESS',
                payment_method_type=payment_type,
                related_rental=rental,
                gateway_response=self._build_payment_gateway_response(
                    points_to_use=points_to_use,
                    points_amount=points_amount,
                    wallet_amount=wallet_amount,
                ),
            )

            if points_to_use > 0:
                from api.user.points.services import deduct_points
                deduct_points(
                    user,
                    points_to_use,
                    'RENTAL_PAYMENT',
                    f"Due payment for rental {rental.rental_code}",
                    async_send=False,
                    related_rental=rental
                )

            if wallet_amount > 0:
                wallet_service = WalletService()
                wallet_service.deduct_balance(
                    user,
                    wallet_amount,
                    f"Due payment for rental {rental.rental_code}",
                    transaction_obj
                )

            rental.overdue_amount = Decimal('0')
            rental.payment_status = 'PAID'
            update_fields = ['overdue_amount', 'payment_status', 'updated_at']

            if is_powerbank_returned:
                rental.status = 'COMPLETED'
                update_fields.append('status')

            rental.save(update_fields=update_fields)

            self._trigger_revenue_distribution(transaction_obj, rental)

            self.log_info(
                f"Rental due paid: {rental.rental_code} for user {user.username} - amount: {total_amount}"
            )
            return transaction_obj

        except Exception as e:
            self.handle_service_error(e, "Failed to pay rental due")

    def _trigger_revenue_distribution(self, transaction_obj, rental) -> None:
        """Trigger revenue distribution for successful payment."""
        try:
            from api.partners.common.services import RevenueDistributionService

            rev_service = RevenueDistributionService()
            distribution = rev_service.create_revenue_distribution(transaction_obj, rental)

            if distribution:
                self.log_info(
                    f"Revenue distribution created for rental {rental.rental_code}: "
                    f"distribution_id={distribution.id}"
                )
        except Exception as e:
            # Log but don't fail the payment; distribution can be recalculated.
            self.log_error(
                f"Failed to create revenue distribution for {rental.rental_code}: {str(e)}"
            )
