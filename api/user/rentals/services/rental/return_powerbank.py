"""
Rental Return Service
=====================

Handles powerbank return with charge calculations and auto-collection.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from api.user.rentals.models import Rental
from api.user.stations.models import Station


class RentalReturnMixin:
    """Mixin for rental return operations"""
    
    @transaction.atomic
    def return_power_bank(self, rental_id: str, return_station_sn: str,
                         return_slot_number: int, battery_level: int = 50) -> Rental:
        """Return power bank to station (Internal use - triggered by hardware)"""
        try:
            rental = Rental.objects.select_for_update().get(id=rental_id)
            
            # Returns can come in after the system has already marked the rental OVERDUE
            if rental.status not in ['ACTIVE', 'OVERDUE']:
                self.log_warning(
                    f"Return already processed for rental {rental.rental_code} (status: {rental.status})"
                )
                return rental
            
            return_station = Station.objects.get(serial_number=return_station_sn)
            return_slot = return_station.slots.get(slot_number=return_slot_number)
            rental.ended_at = timezone.now()
            rental.return_station = return_station
            rental.is_returned_on_time = rental.ended_at <= rental.due_at
            # Rental is returned, mark as COMPLETED regardless of timing
            # Late fees tracked via overdue_amount, not status
            rental.status = 'COMPLETED'
            
            if rental.package.payment_model == 'POSTPAID':
                self._calculate_postpayment_charges(rental)
            
            # Calculate late fees for any late return (PREPAID or POSTPAID)
            if not rental.is_returned_on_time:
                self._calculate_overdue_charges(rental)

            # Battery cycle tracking
            if rental.start_battery_level and battery_level:
                from decimal import Decimal
                from api.user.rentals.models import BatteryCycleLog

                rental.return_battery_level = battery_level

                # Check 5-minute rule
                duration = rental.ended_at - rental.started_at
                if duration.total_seconds() < 300:
                    rental.is_under_5_min = True
                    rental.hardware_issue_reported = True

                # Calculate and log cycle
                discharge = max(0, rental.start_battery_level - battery_level)
                if discharge > 0:
                    cycle_contribution = Decimal(discharge) / Decimal(100)

                    BatteryCycleLog.objects.create(
                        powerbank=rental.power_bank,
                        rental=rental,
                        start_level=rental.start_battery_level,
                        end_level=battery_level,
                        discharge_percent=Decimal(discharge),
                        cycle_contribution=cycle_contribution
                    )

                    # Update powerbank stats
                    rental.power_bank.total_cycles += cycle_contribution
                    rental.power_bank.total_rentals += 1
                    rental.power_bank.save(update_fields=['total_cycles', 'total_rentals', 'updated_at'])
            
            rental.save(update_fields=[
                'status', 'ended_at', 'return_station', 'is_returned_on_time',
                'overdue_amount', 'payment_status',
                'return_battery_level', 'is_under_5_min', 'hardware_issue_reported'
            ])
            
            if rental.payment_status == 'PENDING':
                self._auto_collect_payment(rental)
            
            self._return_powerbank_to_station(rental, return_station, return_slot)
            self._award_completion_points(rental)
            self._send_completion_notification(rental)
            
            self.log_info(f"Power bank returned: {rental.rental_code}")
            return rental
            
        except Exception as e:
            self.handle_service_error(e, "Failed to return power bank")
    
    def _calculate_postpayment_charges(self, rental: Rental) -> None:
        """Calculate charges for post-payment model"""
        if not rental.ended_at or not rental.started_at:
            return
        
        usage_duration = rental.ended_at - rental.started_at
        usage_minutes = int(usage_duration.total_seconds() / 60)
        
        package_rate_per_minute = rental.package.price / rental.package.duration_minutes
        total_cost = Decimal(str(usage_minutes)) * package_rate_per_minute
        
        rental.amount_paid = total_cost
        rental.payment_status = 'PENDING'
    
    def _calculate_overdue_charges(self, rental: Rental) -> None:
        """Calculate overdue charges for late returns"""
        if rental.is_returned_on_time or not rental.ended_at:
            return
        
        from api.common.utils.helpers import (
            calculate_overdue_minutes, calculate_late_fee_amount, get_package_rate_per_minute
        )
        
        overdue_minutes = calculate_overdue_minutes(rental)
        package_rate_per_minute = get_package_rate_per_minute(rental.package)
        rental.overdue_amount = calculate_late_fee_amount(package_rate_per_minute, overdue_minutes)
        
        if rental.overdue_amount > 0:
            rental.payment_status = 'PENDING'
    
    def _auto_collect_payment(self, rental: Rental) -> None:
        """Auto-collect pending payments (POSTPAID charges or late fees)"""
        try:
            from api.user.payments.services import PaymentCalculationService, RentalPaymentService
            
            total_due = rental.amount_paid + rental.overdue_amount
            if total_due <= 0:
                return
            
            calc_service = PaymentCalculationService()
            payment_options = calc_service.calculate_payment_options(
                user=rental.user,
                scenario='post_payment',
                rental_id=str(rental.id)
            )
            
            if payment_options['is_sufficient']:
                payment_service = RentalPaymentService()
                try:
                    transaction = payment_service.pay_rental_due(
                        rental.user, rental, payment_options['payment_breakdown']
                    )
                    self.log_info(f"Auto-collected NPR {total_due} for rental {rental.rental_code}")
                    
                    # Update PENDING transaction if exists
                    self._update_pending_transaction(rental, transaction)
                    
                    # Trigger revenue distribution for POSTPAID
                    self._trigger_revenue_distribution(rental, transaction)
                    
                except Exception as e:
                    self.log_warning(f"Auto-collection failed for {rental.rental_code}: {str(e)}")
                    self._notify_payment_failed(rental, total_due)
            else:
                self.log_info(f"Insufficient balance for auto-collection: {rental.rental_code}")
                self._notify_payment_required(rental, total_due, payment_options['shortfall'])
                
        except Exception as e:
            self.log_error(f"Auto-collection error for {rental.rental_code}: {str(e)}")
            self._notify_payment_required(rental, rental.amount_paid + rental.overdue_amount, Decimal('0'))
    
    def _return_powerbank_to_station(self, rental, return_station, return_slot) -> None:
        """Return power bank to station"""
        from api.user.stations.services import PowerBankService
        powerbank_service = PowerBankService()
        powerbank_service.return_power_bank(
            rental.power_bank, return_station, return_slot, rental=rental
        )
    
    def _update_pending_transaction(self, rental: Rental, payment_transaction) -> None:
        """Update PENDING transaction to SUCCESS if exists"""
        pending_transaction_id = rental.rental_metadata.get('pending_transaction_id')
        if not pending_transaction_id:
            return
        
        try:
            from api.user.payments.models import Transaction
            pending_tx = Transaction.objects.get(
                id=pending_transaction_id,
                status='PENDING'
            )
            pending_tx.status = 'SUCCESS'
            pending_tx.amount = payment_transaction.amount
            pending_tx.payment_method_type = payment_transaction.payment_method_type
            pending_tx.save(update_fields=['status', 'amount', 'payment_method_type'])
            
            self.log_info(
                f"Updated PENDING transaction {pending_tx.transaction_id} to SUCCESS"
            )
        except Exception as e:
            self.log_warning(
                f"Failed to update PENDING transaction for rental {rental.rental_code}: {str(e)}"
            )
    
    def _trigger_revenue_distribution(self, rental: Rental, transaction) -> None:
        """Trigger revenue distribution for POSTPAID rental"""
        try:
            from api.partners.common.services import RevenueDistributionService
            
            rev_service = RevenueDistributionService()
            distribution = rev_service.create_revenue_distribution(transaction, rental)
            
            if distribution:
                self.log_info(
                    f"Revenue distribution created for POSTPAID rental {rental.rental_code}: "
                    f"distribution_id={distribution.id}"
                )
        except Exception as e:
            # Log but don't fail the return - revenue can be recalculated
            self.log_warning(
                f"Failed to create revenue distribution for {rental.rental_code}: {str(e)}"
            )
    
    def _award_completion_points(self, rental: Rental) -> None:
        """Award points for rental completion"""
        from api.user.points.services import award_points
        from api.user.system.services import AppConfigService
        
        config_service = AppConfigService()
        completion_points = int(config_service.get_config_cached('POINTS_RENTAL_COMPLETE', 5))
        
        award_points(
            rental.user, completion_points, 'RENTAL',
            'Rental completion reward',
            async_send=True,
            rental_id=str(rental.id),
            on_time=rental.is_returned_on_time
        )
        
        if rental.is_returned_on_time and not rental.timely_return_bonus_awarded:
            timely_bonus = int(config_service.get_config_cached('POINTS_TIMELY_RETURN', 50))
            
            award_points(
                rental.user, timely_bonus, 'ON_TIME_RETURN',
                f'On-time return bonus for {rental.rental_code}',
                async_send=True
            )
            rental.timely_return_bonus_awarded = True
            rental.save(update_fields=['timely_return_bonus_awarded'])
    
    def _send_completion_notification(self, rental: Rental) -> None:
        """Send rental completion notification"""
        from api.user.notifications.services import notify
        notify(
            rental.user,
            'rental_completed',
            async_send=True,
            powerbank_serial=rental.power_bank.serial_number,
            amount_paid=float(rental.amount_paid),
            rental_code=rental.rental_code
        )
