"""
Rental Cancel Service
=====================

Handles rental cancellation with support for:
- Free cancellation within configurable window (default 5 minutes)
- Late cancellation with fee applied
- PREPAID: Refund minus fee
- POSTPAID: Charge fee from wallet
"""
from __future__ import annotations

from decimal import Decimal
from typing import Tuple

from django.db import transaction
from django.utils import timezone

from api.common.services.base import ServiceException
from api.user.rentals.models import Rental


class RentalCancelMixin:
    """Mixin for rental cancellation operations"""
    
    @transaction.atomic
    def cancel_rental(self, rental_id: str, user, reason: str = "") -> dict:
        """
        Cancel an active rental.
        
        Returns:
            dict with cancellation details:
            - rental: The cancelled rental
            - cancellation_type: 'FREE' or 'LATE'
            - cancellation_fee: Fee charged (0 for free)
            - refund_amount: Amount refunded (PREPAID only)
        """
        try:
            rental = Rental.objects.select_for_update().get(id=rental_id, user=user)
            
            if rental.status not in ['PENDING', 'PENDING_POPUP', 'ACTIVE']:
                raise ServiceException(
                    detail="Rental cannot be cancelled in current status",
                    code="invalid_rental_status"
                )
            
            # Only validate powerbank return for ACTIVE rentals
            if rental.status == 'ACTIVE':
                self._validate_powerbank_returned(rental)
            
            # Check cancellation type (free or with fee)
            is_free, cancellation_fee = self._check_cancellation_type(rental)
            
            # Process payment/refund based on payment model
            refund_amount = self._process_cancellation_payment(
                rental, user, is_free, cancellation_fee
            )
            
            # Update rental status
            rental.status = 'CANCELLED'
            rental.ended_at = timezone.now()
            rental.rental_metadata.update({
                'cancellation_reason': reason,
                'cancellation_type': 'FREE' if is_free else 'LATE',
                'cancellation_fee': str(cancellation_fee),
                'refund_amount': str(refund_amount),
                'cancelled_at': timezone.now().isoformat(),
            })
            rental.save(update_fields=['status', 'ended_at', 'rental_metadata', 'payment_status'])
            
            # Release resources
            self._release_powerbank_and_slot(rental)
            
            # Send notification
            self._send_cancellation_notification(
                user, rental, is_free, cancellation_fee, refund_amount
            )
            
            self.log_info(
                f"Rental cancelled: {rental.rental_code} "
                f"(type={'FREE' if is_free else 'LATE'}, fee={cancellation_fee})"
            )
            
            return {
                'rental': rental,
                'cancellation_type': 'FREE' if is_free else 'LATE',
                'cancellation_fee': cancellation_fee,
                'refund_amount': refund_amount,
            }
            
        except Rental.DoesNotExist:
            raise ServiceException(detail="Rental not found", code="rental_not_found")
        except Exception as e:
            if isinstance(e, ServiceException):
                raise
            self.handle_service_error(e, "Failed to cancel rental")
    
    def _check_cancellation_type(self, rental: Rental) -> Tuple[bool, Decimal]:
        """
        Check if cancellation is free or paid.
        
        Returns:
            Tuple[is_free_cancellation, cancellation_fee]
        """
        # Pending/Pending_popup rentals are always free
        if rental.status in ['PENDING', 'PENDING_POPUP'] or not rental.started_at:
            return True, Decimal('0')
        
        # Get free window from config using AppConfigService
        from api.user.system.services.app_config_service import AppConfigService
        config_service = AppConfigService()
        free_window_minutes = int(config_service.get_config_cached('NO_CHARGE_RENTAL_CANCELLATION_TIME', 5))
        
        time_since_start = timezone.now() - rental.started_at
        usage_minutes = int(time_since_start.total_seconds() / 60)
        
        if usage_minutes <= free_window_minutes:
            return True, Decimal('0')
        
        # Calculate cancellation fee using late fee logic
        chargeable_minutes = usage_minutes - free_window_minutes
        fee = self._calculate_cancellation_fee(rental, chargeable_minutes)
        return False, fee
    
    def _calculate_cancellation_fee(
        self,
        rental: Rental,
        chargeable_minutes: int
    ) -> Decimal:
        """
        Calculate fee for late cancellation.
        
        Uses the same late fee configuration as overdue charges.
        """
        from api.user.rentals.services.late_fee_service import LateFeeService
        
        # Get package rate per minute
        if rental.package:
            normal_rate = rental.package.price / rental.package.duration_minutes
        else:
            # Fallback rate
            normal_rate = Decimal('2.00')
        
        # Get late fee configuration
        config = LateFeeService.get_active_configuration()
        
        # Calculate fee
        fee = LateFeeService.calculate_late_fee(config, normal_rate, chargeable_minutes)
        
        # Cap the fee at the amount paid (for PREPAID) or a reasonable max
        max_fee = rental.amount_paid if rental.amount_paid > 0 else Decimal('500')
        return min(fee, max_fee)
    
    def _process_cancellation_payment(
        self,
        rental: Rental,
        user,
        is_free: bool,
        fee: Decimal
    ) -> Decimal:
        """
        Process payment/refund for cancellation.
        
        Returns:
            refund_amount (for PREPAID) or 0 (for POSTPAID)
        """
        from api.user.payments.services import WalletService
        
        wallet_service = WalletService()
        payment_model = rental.package.payment_model if rental.package else 'PREPAID'
        
        if payment_model == 'PREPAID':
            return self._handle_prepaid_cancellation(
                rental, user, is_free, fee, wallet_service
            )
        else:  # POSTPAID
            return self._handle_postpaid_cancellation(
                rental, user, is_free, fee, wallet_service
            )
    
    def _handle_prepaid_cancellation(
        self,
        rental: Rental,
        user,
        is_free: bool,
        fee: Decimal,
        wallet_service
    ) -> Decimal:
        """Handle PREPAID cancellation refunds"""
        from api.user.payments.models import Transaction
        from api.user.payments.repositories import TransactionRepository
        from api.common.utils.helpers import generate_transaction_id
        
        if rental.payment_status != 'PAID' or rental.amount_paid <= 0:
            rental.payment_status = 'PAID'  # Nothing to refund, mark as settled
            return Decimal('0')
        
        original_txn = Transaction.objects.filter(
            related_rental=rental,
            transaction_type='RENTAL',
            status='SUCCESS'
        ).first()
        
        if is_free:
            # Full refund
            refund_amount = self._refund_full_amount(rental, user, original_txn, wallet_service)
            rental.payment_status = 'REFUNDED'
            return refund_amount
        else:
            # Partial refund (amount - fee)
            refund_amount = rental.amount_paid - fee
            
            if refund_amount > 0:
                # Refund partial amount to wallet
                wallet_service.add_balance(
                    user=user,
                    amount=refund_amount,
                    description=f"Partial refund for cancelled rental {rental.rental_code} (fee: NPR {fee})"
                )
            
            # Create fine transaction for the fee
            self._create_fine_transaction(user, rental, fee, "Late cancellation fee")
            
            # Update original transaction metadata
            if original_txn:
                original_txn.gateway_response.update({
                    'cancellation_fee': str(fee),
                    'refund_amount': str(refund_amount),
                    'cancelled_at': timezone.now().isoformat(),
                })
                original_txn.status = 'PARTIAL_REFUND' if refund_amount > 0 else 'SUCCESS'
                original_txn.save(update_fields=['gateway_response', 'status', 'updated_at'])
                
                # Create reversal distribution for refunded amount
                if refund_amount > 0:
                    self._create_reversal_distribution(original_txn, refund_amount, 'PARTIAL_REFUND')
            
            rental.payment_status = 'PAID'  # Fee retained
            return refund_amount
    
    def _handle_postpaid_cancellation(
        self,
        rental: Rental,
        user,
        is_free: bool,
        fee: Decimal,
        wallet_service
    ) -> Decimal:
        """Handle POSTPAID cancellation charges"""
        if is_free:
            # No payment needed
            rental.payment_status = 'PAID'  # No dues
            return Decimal('0')
        else:
            # Check user wallet balance
            wallet_balance = Decimal('0')
            if hasattr(user, 'wallet') and user.wallet:
                wallet_balance = user.wallet.balance
            
            if wallet_balance < fee:
                shortfall = fee - wallet_balance
                raise ServiceException(
                    detail=f"Insufficient balance. Add NPR {shortfall} to cancel this rental.",
                    code="insufficient_balance_for_cancellation"
                )
            
            # Deduct fee from wallet
            wallet_service.deduct_balance(
                user=user,
                amount=fee,
                description=f"Late cancellation fee for rental {rental.rental_code}"
            )
            
            # Create fine transaction
            self._create_fine_transaction(user, rental, fee, "Late cancellation fee")
            
            rental.amount_paid = fee
            rental.payment_status = 'PAID'
            return Decimal('0')  # No refund for POSTPAID
    
    def _refund_full_amount(
        self,
        rental: Rental,
        user,
        original_txn,
        wallet_service
    ) -> Decimal:
        """Process full refund for free cancellation"""
        if not original_txn:
            # Fallback: refund amount_paid to wallet
            wallet_service.add_balance(
                user=user,
                amount=rental.amount_paid,
                description=f"Full refund for cancelled rental {rental.rental_code}"
            )
            return rental.amount_paid
        
        payment_method = original_txn.payment_method_type
        refund_amount = Decimal('0')
        
        # Refund points if used
        if payment_method in ['POINTS', 'COMBINATION']:
            points_used = original_txn.gateway_response.get('points_used', 0)
            if points_used > 0:
                from api.user.points.services import award_points
                award_points(
                    user, points_used, 'REFUND',
                    f'Points refund for cancelled rental {rental.rental_code}',
                    async_send=False
                )
        
        # Refund wallet amount
        if payment_method in ['WALLET', 'COMBINATION']:
            wallet_amount = Decimal(str(
                original_txn.gateway_response.get('wallet_amount', rental.amount_paid)
            ))
            if wallet_amount > 0:
                wallet_service.add_balance(
                    user=user,
                    amount=wallet_amount,
                    description=f"Full refund for cancelled rental {rental.rental_code}"
                )
                refund_amount = wallet_amount
        
        # Update original transaction
        original_txn.status = 'REFUNDED'
        original_txn.gateway_response['refunded_at'] = timezone.now().isoformat()
        original_txn.save(update_fields=['status', 'gateway_response', 'updated_at'])
        
        # Create reversal distribution for full refund
        if refund_amount > 0:
            self._create_reversal_distribution(original_txn, refund_amount, 'FULL_REFUND')
        
        return refund_amount
    
    def _create_fine_transaction(
        self,
        user,
        rental: Rental,
        amount: Decimal,
        description: str
    ) -> None:
        """Create a FINE transaction for cancellation fee"""
        from api.user.payments.repositories import TransactionRepository
        from api.common.utils.helpers import generate_transaction_id
        
        TransactionRepository.create(
            user=user,
            transaction_id=generate_transaction_id(),
            transaction_type='FINE',
            amount=amount,
            status='SUCCESS',
            payment_method_type='WALLET',
            related_rental=rental,
            gateway_response={
                'description': description,
                'rental_code': rental.rental_code,
            }
        )
    
    def _validate_powerbank_returned(self, rental: Rental) -> None:
        """Verify powerbank is physically back in station"""
        if not rental.power_bank:
            return
        
        if rental.power_bank.current_station != rental.station:
            raise ServiceException(
                detail="Cannot cancel rental. Please return powerbank to station first.",
                code="powerbank_not_returned"
            )
        
        if rental.power_bank.current_slot is None:
            raise ServiceException(
                detail="Cannot cancel rental. Powerbank not detected in any slot.",
                code="powerbank_not_in_slot"
            )
        
        if rental.slot and rental.slot.status != 'OCCUPIED':
            raise ServiceException(
                detail="Cannot cancel rental. Powerbank must be inserted back in slot.",
                code="slot_not_occupied"
            )
        
        # Warn if location data is stale but don't block
        if rental.power_bank.updated_at:
            time_since_update = timezone.now() - rental.power_bank.updated_at
            if time_since_update.total_seconds() > 60:
                self.log_warning(
                    f"Powerbank {rental.power_bank.serial_number} location data is stale "
                    f"({time_since_update.total_seconds():.0f}s old). Allowing cancellation with caution."
                )
    
    def _release_powerbank_and_slot(self, rental: Rental) -> None:
        """Release power bank and slot back to available"""
        if rental.power_bank:
            rental.power_bank.status = 'AVAILABLE'
            rental.power_bank.current_station = rental.station
            rental.power_bank.current_slot = rental.slot
            rental.power_bank.save(update_fields=['status', 'current_station', 'current_slot'])
        
        if rental.slot:
            rental.slot.status = 'AVAILABLE'
            rental.slot.current_rental = None
            rental.slot.save(update_fields=['status', 'current_rental'])
    
    def _create_reversal_distribution(self, transaction, refund_amount: Decimal, reason: str) -> None:
        """Create reversal distribution for refund"""
        try:
            from api.partners.common.services import RevenueDistributionService
            from api.partners.common.repositories import RevenueDistributionRepository
            
            original_dist = RevenueDistributionRepository.get_by_transaction_id(str(transaction.id))
            if original_dist:
                service = RevenueDistributionService()
                service.create_reversal_distribution(
                    original_distribution_id=str(original_dist.id),
                    refund_amount=refund_amount,
                    reason=reason
                )
        except Exception as e:
            self.log_error(f"Failed to create reversal distribution: {str(e)}")
    
    def _send_cancellation_notification(
        self,
        user,
        rental: Rental,
        is_free: bool,
        fee: Decimal,
        refund_amount: Decimal
    ) -> None:
        """Send cancellation notification"""
        from api.user.notifications.services import notify
        
        if is_free:
            template = 'rental_cancelled_free'
        elif rental.package and rental.package.payment_model == 'POSTPAID':
            template = 'rental_cancelled_postpaid'
        else:
            template = 'rental_cancelled_late'
        
        notify(
            user,
            template,
            async_send=True,
            rental_code=rental.rental_code,
            cancellation_fee=float(fee),
            refund_amount=float(refund_amount),
            amount_paid=float(rental.amount_paid),
        )
