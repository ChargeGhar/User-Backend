"""
Rental Extend Service
=====================

Handles rental duration extensions.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from api.common.services.base import ServiceException
from api.user.rentals.models import Rental, RentalExtension, RentalPackage


class RentalExtendMixin:
    """Mixin for rental extension operations"""
    
    @transaction.atomic
    def extend_rental(self, rental_id: str, user, package_id: str) -> RentalExtension:
        """Extend rental duration"""
        try:
            rental = Rental.objects.select_for_update().get(id=rental_id, user=user)
            package = RentalPackage.objects.get(id=package_id, is_active=True)
            
            self._validate_extension_allowed(rental)
            extension_count = self._validate_extension_limit(rental)
            self._process_extension_payment(user, package, rental)
            
            extension = RentalExtension.objects.create(
                rental=rental,
                package=package,
                created_by=user,
                extended_minutes=package.duration_minutes,
                extension_cost=package.price
            )
            
            old_due_at = rental.due_at
            rental.due_at += timezone.timedelta(minutes=package.duration_minutes)
            rental.amount_paid += package.price
            rental.save(update_fields=['due_at', 'amount_paid'])
            
            self._send_extension_notification(user, rental, package, old_due_at)
            
            self.log_info(
                f"Rental extended: {rental.rental_code} by {package.duration_minutes} minutes "
                f"(Extension #{extension_count + 1})"
            )
            return extension
            
        except (Rental.DoesNotExist, RentalPackage.DoesNotExist):
            raise ServiceException(detail="Rental or package not found", code="not_found")
        except Exception as e:
            self.handle_service_error(e, "Failed to extend rental")
    
    def _validate_extension_allowed(self, rental: Rental) -> None:
        """Validate rental can be extended"""
        if rental.status != 'ACTIVE':
            raise ServiceException(
                detail="Only active rentals can be extended",
                code="invalid_rental_status"
            )
        
        if timezone.now() >= rental.due_at:
            raise ServiceException(
                detail="Cannot extend overdue rental. Please return powerbank.",
                code="rental_overdue"
            )
    
    def _validate_extension_limit(self, rental: Rental) -> int:
        """Check extension limit and return current count"""
        from api.user.system.models import AppConfig
        
        max_extensions = int(AppConfig.objects.filter(
            key='MAX_RENTAL_EXTENSIONS', is_active=True
        ).values_list('value', flat=True).first() or 3)
        
        extension_count = rental.extensions.count()
        
        if extension_count >= max_extensions:
            raise ServiceException(
                detail=f"Maximum {max_extensions} extensions allowed per rental",
                code="max_extensions_reached"
            )
        
        return extension_count
    
    def _process_extension_payment(self, user, package: RentalPackage, rental: Rental) -> None:
        """Process payment for extension"""
        from api.user.payments.services import PaymentCalculationService, RentalPaymentService
        
        calc_service = PaymentCalculationService()
        payment_options = calc_service.calculate_payment_options(
            user=user,
            scenario='pre_payment',
            package_id=str(package.id)
        )
        
        if not payment_options['is_sufficient']:
            raise ServiceException(
                detail=f"Insufficient balance for extension. Need NPR {payment_options['shortfall']} more.",
                code="insufficient_balance"
            )
        
        payment_service = RentalPaymentService()
        payment_service.process_rental_payment(
            user=user,
            rental=rental,
            payment_breakdown=payment_options['payment_breakdown']
        )
    
    def _send_extension_notification(self, user, rental, package, old_due_at) -> None:
        """Send extension notification"""
        from api.user.notifications.services import notify
        notify(
            user,
            'rental_extended',
            async_send=True,
            rental_code=rental.rental_code,
            extended_minutes=package.duration_minutes,
            extension_cost=float(package.price),
            old_due_time=old_due_at.strftime('%H:%M'),
            new_due_time=rental.due_at.strftime('%H:%M')
        )
