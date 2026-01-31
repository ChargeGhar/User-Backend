"""
Rental Start Service - Core Implementation
==========================================

Main orchestrator mixin for rental start flow.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from api.common.services.base import ServiceException
from api.common.utils.helpers import generate_rental_code
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station

from .validation import (
    validate_rental_prerequisites,
    validate_station_availability,
    validate_postpaid_balance,
    get_available_power_bank_and_slot,
    validate_powerbank_for_rental,
)
from .payment import process_prepayment
from .device import trigger_device_popup, activate_rental_powerbank
from .discount import (
    get_applicable_discount,
    build_discount_metadata,
    record_discount_usage,
)
from .vendor_ejection import check_vendor_free_ejection, log_vendor_free_ejection
from .revenue import trigger_revenue_distribution


class RentalStartMixin:
    """
    Mixin for rental start operations.
    
    Inherited by RentalService to provide start_rental() method.
    """
    
    @transaction.atomic
    def start_rental(
        self,
        user,
        station_sn: str,
        package_id: str,
        powerbank_sn: Optional[str] = None
    ) -> Rental:
        """
        Start a new rental session with device popup.
        
        Flow:
        1. Validate user and station
        2. Get discount if applicable
        3. Create rental in PENDING_POPUP status
        4. Process payment (if PREPAID)
        5. Trigger device popup (sync, 15s timeout)
        6. If popup succeeds -> ACTIVE + revenue distribution
        7. If popup times out -> PENDING_POPUP + async verification
        
        Args:
            user: User starting rental
            station_sn: Station serial number
            package_id: Rental package ID
            powerbank_sn: Optional specific powerbank SN (if user selected)
        
        Returns:
            Rental object
        """
        try:
            # Step 1: Validation
            validate_rental_prerequisites(user)
            
            station = Station.objects.get(serial_number=station_sn)
            package = RentalPackage.objects.get(id=package_id, is_active=True)
            
            validate_station_availability(station)
            
            if package.payment_model == 'POSTPAID':
                validate_postpaid_balance(user)
            
            power_bank, slot = get_available_power_bank_and_slot(station)
            
            # Step 2: Get discount
            discount, discount_amount, actual_price = get_applicable_discount(
                station_sn, package_id, user
            )
            
            if discount:
                self.log_info(
                    f"Discount applied: {discount.discount_percent}% off, "
                    f"original: {package.price}, final: {actual_price}"
                )
            
            # Step 3: Create rental
            rental_metadata = build_discount_metadata(
                discount, package.price, discount_amount, actual_price
            )
            
            rental = Rental.objects.create(
                user=user,
                station=station,
                slot=slot,
                package=package,
                power_bank=power_bank,
                rental_code=generate_rental_code(),
                status='PENDING_POPUP',
                due_at=timezone.now() + timezone.timedelta(minutes=package.duration_minutes),
                amount_paid=Decimal('0'),
                rental_metadata=rental_metadata
            )
            
            # Step 4: Process payment (PREPAID only)
            transaction = None
            if package.payment_model == 'PREPAID':
                transaction = process_prepayment(user, package, rental, actual_price)
                rental.amount_paid = actual_price
                rental.payment_status = 'PAID'
                rental.save(update_fields=['amount_paid', 'payment_status'])
            else:
                # Create PENDING transaction for POSTPAID
                from .payment import create_postpaid_transaction
                transaction = create_postpaid_transaction(user, rental, actual_price)
                rental.rental_metadata['pending_transaction_id'] = str(transaction.id)
                rental.save(update_fields=['rental_metadata'])
            
            # Step 5: Trigger device popup
            popup_success, popup_result_sn = trigger_device_popup(
                rental, station, power_bank, powerbank_sn
            )
            
            # Step 6: Handle popup result
            if popup_success:
                self._handle_popup_success(
                    rental=rental,
                    station=station,
                    package=package,
                    user=user,
                    popup_result_sn=popup_result_sn,
                    discount=discount,
                    actual_price=actual_price
                )
            else:
                # Popup pending verification
                self.log_warning(f"Rental {rental.rental_code} popup pending verification")
            
            return rental
            
        except Exception as e:
            if isinstance(e, ServiceException):
                raise
            self.handle_service_error(e, "Failed to start rental")
    
    def _handle_popup_success(
        self,
        rental: Rental,
        station: Station,
        package: RentalPackage,
        user,
        popup_result_sn: str,
        discount,
        actual_price: Decimal
    ) -> None:
        """Handle successful popup - activate rental and trigger post-activation tasks."""
        # Validate and get actual powerbank
        actual_power_bank = validate_powerbank_for_rental(
            rental.power_bank, station, popup_result_sn
        )
        
        # Update rental with actual powerbank/slot
        if actual_power_bank.current_slot_id:
            rental.slot = actual_power_bank.current_slot
        
        rental.power_bank = actual_power_bank
        
        # Assign powerbank to rental
        activate_rental_powerbank(rental, actual_power_bank)
        
        # Activate rental
        rental.status = 'ACTIVE'
        rental.started_at = timezone.now()
        rental.rental_metadata['popup_sn'] = popup_result_sn
        rental.save(update_fields=['status', 'started_at', 'rental_metadata', 'power_bank', 'slot'])
        
        # Post-activation tasks
        
        # Record discount usage
        if discount:
            record_discount_usage(discount, user, rental, package.price)
            self._send_discount_notification(user, rental, discount, package.price, actual_price)
        
        # Check and log vendor free ejection (BR13.2)
        if check_vendor_free_ejection(user, station):
            log_vendor_free_ejection(user, station, rental, actual_power_bank)
            self.log_info(f"Vendor free ejection logged for rental {rental.rental_code}")
        
        # Trigger revenue distribution for PREPAID
        if package.payment_model == 'PREPAID':
            trigger_revenue_distribution(rental)
        
        # Send notifications
        self._schedule_reminder_notification(user, rental)
        self._send_rental_started_notification(user, actual_power_bank, station)
        
        self.log_info(f"Rental started: {rental.rental_code} by {user.username}")
