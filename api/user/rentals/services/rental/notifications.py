"""
Rental Notification Helpers
===========================

Notification methods used across rental operations.
"""
from __future__ import annotations

from decimal import Decimal


class RentalNotificationMixin:
    """Mixin for rental notification methods"""
    
    def _notify_payment_failed(self, rental, amount: Decimal) -> None:
        """Notify user that auto-payment failed"""
        try:
            from api.user.notifications.services import notify
            notify(
                rental.user,
                'payment_failed',
                async_send=True,
                rental_code=rental.rental_code,
                amount=float(amount),
                reason='Auto-payment processing failed'
            )
        except Exception as e:
            self.log_error(f"Failed to send payment failed notification: {str(e)}")
    
    def _notify_payment_required(self, rental, amount: Decimal, shortfall: Decimal) -> None:
        """Notify user to pay manually"""
        try:
            from api.user.notifications.services import notify
            notify(
                rental.user,
                'payment_due',
                async_send=True,
                rental_code=rental.rental_code,
                amount=float(amount),
                shortfall=float(shortfall),
                message=f"Outstanding dues for rental {rental.rental_code}. Please add NPR {shortfall} to your account."
            )
        except Exception as e:
            self.log_error(f"Failed to send payment required notification: {str(e)}")
    
    def _send_rental_started_notification(self, user, power_bank, station) -> None:
        """Send rental start notification"""
        from api.user.notifications.services import notify
        notify(
            user,
            'rental_started',
            async_send=True,
            powerbank_serial=power_bank.serial_number,
            station_name=station.station_name,
            rental_duration=24
        )
    
    def _schedule_reminder_notification(self, user, rental) -> None:
        """Schedule reminder notification 15 minutes before due"""
        from django.utils import timezone
        
        reminder_time = rental.due_at - timezone.timedelta(minutes=15)
        if reminder_time > timezone.now():
            from api.user.notifications.tasks import send_notification_task
            send_notification_task.apply_async(
                args=[str(user.id), 'rental_reminder', {
                    'rental_id': str(rental.id),
                    'rental_code': rental.rental_code,
                    'due_time': rental.due_at.strftime('%H:%M')
                }],
                eta=reminder_time
            )
    
    def _send_discount_notification(self, user, rental, discount, original_price, final_price) -> None:
        """Send discount applied notification"""
        try:
            from api.user.notifications.services import notify
            from decimal import Decimal
            discount_amount = Decimal(str(original_price)) - Decimal(str(final_price))
            notify(
                user,
                'discount_applied',
                async_send=True,
                rental_code=rental.rental_code,
                discount_percent=float(discount.discount_percent),
                original_price=float(original_price),
                discount_amount=float(discount_amount),
                final_price=float(final_price),
                station_name=discount.station.station_name
            )
        except Exception as e:
            self.log_error(f"Failed to send discount notification: {str(e)}")
