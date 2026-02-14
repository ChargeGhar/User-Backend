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
from api.user.payments.models import Transaction
from api.user.payments.services import WalletService
from api.user.payments.repositories import TransactionRepository
from api.user.system.services.app_config_service import AppConfigService
from api.user.rentals.services.late_fee_service import LateFeeService
from api.user.points.services.points_service import PointsService
from api.user.notifications.services import notify
from api.common.utils.helpers import generate_transaction_id


class RentalCancelMixin:
    """Mixin for rental cancellation operations"""
    
    @transaction.atomic
    def cancel_rental(self, rental_id: str, user, reason: str = "") -> dict:
        """Cancel an active rental with automatic fee calculation and refund processing"""
        try:
            rental = Rental.objects.select_for_update().get(id=rental_id, user=user)
            
            if rental.status not in ['PENDING', 'PENDING_POPUP', 'ACTIVE']:
                raise ServiceException(detail="Rental cannot be cancelled in current status", code="invalid_rental_status")
            
            if rental.status == 'ACTIVE':
                self._validate_powerbank_returned(rental)
            
            is_free, cancellation_fee = self._check_cancellation_type(rental)
            refund_amount = self._process_cancellation_payment(rental, user, is_free, cancellation_fee)
            
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
            
            self._release_powerbank_and_slot(rental)
            self._send_cancellation_notification(user, rental, is_free, cancellation_fee, refund_amount)
            
            self.log_info(f"Rental cancelled: {rental.rental_code} (type={'FREE' if is_free else 'LATE'}, fee={cancellation_fee})")
            
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
        """Check if cancellation is free or paid - Returns (is_free, fee)"""
        if rental.status in ['PENDING', 'PENDING_POPUP'] or not rental.started_at:
            return True, Decimal('0')
        
        free_window = int(AppConfigService().get_config_cached('NO_CHARGE_RENTAL_CANCELLATION_TIME', 5))
        usage_minutes = int((timezone.now() - rental.started_at).total_seconds() / 60)
        
        if usage_minutes <= free_window:
            return True, Decimal('0')
        
        chargeable_minutes = usage_minutes - free_window
        normal_rate = rental.package.price / rental.package.duration_minutes if rental.package else Decimal('2.00')
        config = LateFeeService.get_active_configuration()
        fee = LateFeeService.calculate_late_fee(config, normal_rate, chargeable_minutes)
        max_fee = rental.amount_paid if rental.amount_paid > 0 else Decimal('500')
        
        return False, min(fee, max_fee)
    
    def _process_cancellation_payment(self, rental: Rental, user, is_free: bool, fee: Decimal) -> Decimal:
        """Process payment/refund for cancellation - Returns refund_amount"""
        wallet_service = WalletService()
        payment_model = rental.package.payment_model if rental.package else 'PREPAID'
        
        return (self._handle_prepaid_cancellation(rental, user, is_free, fee, wallet_service) 
                if payment_model == 'PREPAID' 
                else self._handle_postpaid_cancellation(rental, user, is_free, fee, wallet_service))
    
    def _handle_prepaid_cancellation(self, rental: Rental, user, is_free: bool, fee: Decimal, wallet_service) -> Decimal:
        """Handle PREPAID cancellation refunds"""
        if rental.payment_status != 'PAID' or rental.amount_paid <= 0:
            rental.payment_status = 'PAID'
            return Decimal('0')
        
        original_txn = Transaction.objects.filter(related_rental=rental, transaction_type='RENTAL', status='SUCCESS').first()
        
        if is_free:
            refund = self._refund_full_amount(rental, user, original_txn, wallet_service)
            rental.payment_status = 'REFUNDED'
            return refund
        
        refund_amount = rental.amount_paid - fee
        
        if refund_amount > 0:
            wallet_service.add_balance(user, refund_amount, 
                description=f"Partial refund for cancelled rental {rental.rental_code} (fee: NPR {fee})")
        
        self._create_fine_transaction(user, rental, fee, "Late cancellation fee")
        
        if original_txn:
            original_txn.gateway_response.update({
                'cancellation_fee': str(fee),
                'refund_amount': str(refund_amount),
                'cancelled_at': timezone.now().isoformat(),
            })
            original_txn.status = 'REFUNDED' if refund_amount > 0 else 'SUCCESS'
            original_txn.save(update_fields=['gateway_response', 'status', 'updated_at'])
            
            if refund_amount > 0:
                self._create_reversal_distribution(original_txn, refund_amount, 'PARTIAL_REFUND')
        
        rental.payment_status = 'PAID'
        return refund_amount
    
    def _handle_postpaid_cancellation(self, rental: Rental, user, is_free: bool, fee: Decimal, wallet_service) -> Decimal:
        """Handle POSTPAID cancellation charges"""
        if is_free:
            self._mark_postpaid_start_transaction_failed(rental, fee=Decimal('0'))
            rental.payment_status = 'PAID'
            return Decimal('0')
        
        wallet_balance = user.wallet.balance if hasattr(user, 'wallet') and user.wallet else Decimal('0')
        
        if wallet_balance < fee:
            raise ServiceException(detail=f"Insufficient balance. Add NPR {fee - wallet_balance} to cancel this rental.",
                code="insufficient_balance_for_cancellation")
        
        wallet_service.deduct_balance(user, fee, description=f"Late cancellation fee for rental {rental.rental_code}")
        self._create_fine_transaction(user, rental, fee, "Late cancellation fee")
        self._mark_postpaid_start_transaction_failed(rental, fee=fee)
        
        rental.amount_paid = fee
        rental.payment_status = 'PAID'
        return Decimal('0')
    
    def _refund_full_amount(self, rental: Rental, user, original_txn, wallet_service) -> Decimal:
        """Process full refund for free cancellation"""
        if not original_txn:
            raise ServiceException(detail="Original rental payment transaction not found", 
                code="missing_original_payment_transaction")

        gateway = original_txn.gateway_response or {}
        required = ('wallet_amount', 'points_used', 'total_amount')
        
        if missing := [k for k in required if k not in gateway]:
            raise ServiceException(detail=f"Missing payment metadata: {', '.join(missing)}", code="invalid_refund_metadata")

        try:
            wallet_refund = Decimal(str(gateway['wallet_amount'])).quantize(Decimal('0.01'))
            points_refund = int(gateway['points_used'])
            total_refund = Decimal(str(gateway['total_amount'])).quantize(Decimal('0.01'))
        except (ValueError, TypeError, ArithmeticError):
            raise ServiceException(detail="Invalid payment metadata values", code="invalid_refund_metadata")

        if wallet_refund < 0 or points_refund < 0 or total_refund < 0:
            raise ServiceException(detail="Refund metadata cannot be negative", code="invalid_refund_metadata")

        txn_amount = Decimal(str(original_txn.amount)).quantize(Decimal('0.01'))
        if total_refund != txn_amount:
            raise ServiceException(detail=f"Refund mismatch: total={total_refund}, transaction={txn_amount}", 
                code="invalid_refund_metadata")

        payment_method = original_txn.payment_method_type
        if payment_method == 'WALLET' and points_refund != 0:
            raise ServiceException(detail="Wallet transaction has unexpected points", code="invalid_refund_metadata")
        if payment_method == 'POINTS' and wallet_refund != Decimal('0.00'):
            raise ServiceException(detail="Points transaction has unexpected wallet amount", code="invalid_refund_metadata")
        if payment_method == 'COMBINATION' and (wallet_refund <= Decimal('0.00') or points_refund <= 0):
            raise ServiceException(detail="Combination requires both wallet and points", code="invalid_refund_metadata")

        if wallet_refund > 0:
            wallet_service.add_balance(
                user=user,
                amount=wallet_refund,
                description=f"Full refund for cancelled rental {rental.rental_code}",
                transaction_obj=original_txn,
            )

        if points_refund > 0:
            PointsService().adjust_points(
                user=user,
                points=points_refund,
                adjustment_type='ADD',
                reason=f'Points refund for cancelled rental {rental.rental_code}',
                source='RENTAL_PAYMENT',
                related_rental=rental,
                metadata={
                    'refund_for_transaction_id': str(original_txn.id),
                    'refund_for_rental_id': str(rental.id),
                },
            )
        
        original_txn.status = 'REFUNDED'
        original_txn.gateway_response.update({
            'refunded_at': timezone.now().isoformat(),
            'refund_amount': str(total_refund),
            'refund_wallet_amount': str(wallet_refund),
            'refund_points_used': points_refund,
        })
        original_txn.save(update_fields=['status', 'gateway_response', 'updated_at'])
        
        if total_refund > 0:
            self._create_reversal_distribution(original_txn, total_refund, 'FULL_REFUND')
        
        return total_refund

    def _mark_postpaid_start_transaction_failed(self, rental: Rental, fee: Decimal) -> None:
        """Close POSTPAID start transaction on cancellation to avoid stale pending records."""
        pending_txn = Transaction.objects.filter(
            related_rental=rental,
            transaction_type='RENTAL',
            status='PENDING',
        ).first()
        if not pending_txn:
            return

        gateway = pending_txn.gateway_response or {}
        gateway.update({
            'cancelled_at': timezone.now().isoformat(),
            'cancelled_rental': True,
            'cancellation_fee': str(fee.quantize(Decimal('0.01'))),
        })
        pending_txn.status = 'FAILED'
        pending_txn.gateway_response = gateway
        pending_txn.save(update_fields=['status', 'gateway_response', 'updated_at'])
    
    def _create_fine_transaction(self, user, rental: Rental, amount: Decimal, description: str) -> None:
        """Create FINE transaction for cancellation fee"""
        TransactionRepository.create(
            user=user,
            transaction_id=generate_transaction_id(),
            transaction_type='FINE',
            amount=amount,
            status='SUCCESS',
            payment_method_type='WALLET',
            related_rental=rental,
            gateway_response={'description': description, 'rental_code': rental.rental_code}
        )
    
    def _validate_powerbank_returned(self, rental: Rental) -> None:
        """Verify powerbank is physically back in station"""
        if not rental.power_bank:
            return
        
        if rental.power_bank.current_station != rental.station:
            raise ServiceException(detail="Cannot cancel rental. Please return powerbank to station first.",
                code="powerbank_not_returned")
        
        if rental.power_bank.current_slot is None:
            raise ServiceException(detail="Cannot cancel rental. Powerbank not detected in any slot.",
                code="powerbank_not_in_slot")
        
        if rental.slot and rental.slot.status != 'OCCUPIED':
            raise ServiceException(detail="Cannot cancel rental. Powerbank must be inserted back in slot.",
                code="slot_not_occupied")
        
        if rental.power_bank.updated_at and (time_diff := (timezone.now() - rental.power_bank.updated_at).total_seconds()) > 60:
            self.log_warning(f"Powerbank {rental.power_bank.serial_number} location data stale ({time_diff:.0f}s). Allowing cancellation.")
    
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
            
            if original_dist := RevenueDistributionRepository.get_by_transaction_id(str(transaction.id)):
                RevenueDistributionService().create_reversal_distribution(
                    original_distribution_id=str(original_dist.id),
                    refund_amount=refund_amount,
                    reason=reason
                )
        except Exception as e:
            self.log_error(f"Failed to create reversal distribution: {str(e)}")
    
    def _send_cancellation_notification(self, user, rental: Rental, is_free: bool, fee: Decimal, refund_amount: Decimal) -> None:
        """Send cancellation notification"""
        if is_free:
            template = 'rental_cancelled_free'
        elif rental.package and rental.package.payment_model == 'POSTPAID':
            template = 'rental_cancelled_postpaid'
        else:
            template = 'rental_cancelled_late'
        
        notify(user, template, async_send=True, rental_code=rental.rental_code,
            cancellation_fee=float(fee), refund_amount=float(refund_amount), amount_paid=float(rental.amount_paid))
