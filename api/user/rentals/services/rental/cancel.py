"""
Rental Cancel Service
=====================

Handles rental cancellation with refund processing.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from api.common.services.base import ServiceException
from api.user.rentals.models import Rental


class RentalCancelMixin:
    """Mixin for rental cancellation operations"""
    
    @transaction.atomic
    def cancel_rental(self, rental_id: str, user, reason: str = "") -> Rental:
        """Cancel an active rental"""
        try:
            rental = Rental.objects.get(id=rental_id, user=user)
            
            if rental.status not in ['PENDING', 'PENDING_POPUP', 'ACTIVE']:
                raise ServiceException(
                    detail="Rental cannot be cancelled in current status",
                    code="invalid_rental_status"
                )
            
            self._validate_cancellation_window(rental)
            self._validate_powerbank_returned(rental)
            
            rental.status = 'CANCELLED'
            rental.ended_at = timezone.now()
            rental.rental_metadata['cancellation_reason'] = reason
            rental.save(update_fields=['status', 'ended_at', 'rental_metadata'])
            
            self._release_powerbank_and_slot(rental)
            self._process_cancellation_refund(rental, user)
            
            self.log_info(f"Rental cancelled: {rental.rental_code}")
            return rental
            
        except Rental.DoesNotExist:
            raise ServiceException(detail="Rental not found", code="rental_not_found")
        except Exception as e:
            self.handle_service_error(e, "Failed to cancel rental")
    
    def _validate_cancellation_window(self, rental: Rental) -> None:
        """Check if rental can be cancelled within time window"""
        if not rental.started_at:
            return
        
        from api.user.system.models import AppConfig
        
        cancellation_window_minutes = int(AppConfig.objects.filter(
            key='RENTAL_CANCELLATION_WINDOW_MINUTES', is_active=True
        ).values_list('value', flat=True).first() or 5)
        
        time_since_start = timezone.now() - rental.started_at
        
        if time_since_start.total_seconds() > (cancellation_window_minutes * 60):
            raise ServiceException(
                detail=f"Rental can only be cancelled within {cancellation_window_minutes} minutes of start",
                code="cancellation_time_expired"
            )
    
    def _validate_powerbank_returned(self, rental: Rental) -> None:
        """Verify powerbank is physically back in station"""
        if not rental.power_bank or rental.status != 'ACTIVE':
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
        
        if rental.slot.status != 'OCCUPIED':
            raise ServiceException(
                detail="Cannot cancel rental. Powerbank must be inserted back in slot.",
                code="slot_not_occupied"
            )
        
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
    
    def _process_cancellation_refund(self, rental: Rental, user) -> None:
        """Process refund for cancelled rental"""
        if rental.payment_status != 'PAID' or rental.amount_paid <= 0:
            return
        
        from api.user.payments.models import Transaction
        from api.user.payments.services import WalletService
        
        original_txn = Transaction.objects.filter(
            related_rental=rental,
            transaction_type='RENTAL',
            status='SUCCESS'
        ).first()
        
        if original_txn:
            payment_method = original_txn.payment_method_type
            
            if payment_method in ['POINTS', 'COMBINATION']:
                points_used = original_txn.gateway_response.get('points_used', 0)
                if points_used > 0:
                    from api.user.points.services import award_points
                    award_points(
                        user, points_used, 'REFUND',
                        f'Points refund for cancelled rental {rental.rental_code}',
                        async_send=False
                    )
            
            if payment_method in ['WALLET', 'COMBINATION']:
                wallet_amount = original_txn.gateway_response.get('wallet_amount', rental.amount_paid)
                wallet_service = WalletService()
                wallet_service.add_balance(
                    user=user,
                    amount=wallet_amount,
                    description=f"Wallet refund for cancelled rental {rental.rental_code}"
                )
            
            original_txn.status = 'REFUNDED'
            original_txn.save(update_fields=['status'])
            
            rental.payment_status = 'REFUNDED'
            rental.save(update_fields=['payment_status'])
        else:
            wallet_service = WalletService()
            wallet_service.add_balance(
                user=user,
                amount=rental.amount_paid,
                description=f"Refund for cancelled rental {rental.rental_code}"
            )
