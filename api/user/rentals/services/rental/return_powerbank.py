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
            
            rental.status = 'COMPLETED' if rental.is_returned_on_time else 'OVERDUE'
            
            if rental.package.payment_model == 'POSTPAID':
                self._calculate_postpayment_charges(rental)
            elif not rental.is_returned_on_time:
                self._calculate_overdue_charges(rental)
            
            rental.save(update_fields=[
                'status', 'ended_at', 'return_station', 'is_returned_on_time',
                'overdue_amount', 'payment_status'
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
                    payment_service.pay_rental_due(
                        rental.user, rental, payment_options['payment_breakdown']
                    )
                    self.log_info(f"Auto-collected NPR {total_due} for rental {rental.rental_code}")
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
    
    def _award_completion_points(self, rental: Rental) -> None:
        """Award points for rental completion"""
        from api.user.points.services import award_points
        from api.user.system.models import AppConfig
        
        completion_points = int(AppConfig.objects.filter(
            key='POINTS_RENTAL_COMPLETE', is_active=True
        ).values_list('value', flat=True).first() or 5)
        
        award_points(
            rental.user, completion_points, 'RENTAL',
            'Rental completion reward',
            async_send=True,
            rental_id=str(rental.id),
            on_time=rental.is_returned_on_time
        )
        
        if rental.is_returned_on_time and not rental.timely_return_bonus_awarded:
            timely_bonus = int(AppConfig.objects.filter(
                key='POINTS_TIMELY_RETURN', is_active=True
            ).values_list('value', flat=True).first() or 50)
            
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
