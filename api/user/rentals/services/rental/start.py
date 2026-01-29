"""
Rental Start Service
====================

Handles starting new rentals with validation, payment, and device popup.
"""
from __future__ import annotations

from typing import Tuple, Optional
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from api.common.services.base import ServiceException
from api.common.utils.helpers import generate_rental_code
from api.common.permissions.base import CanRentPowerBank
from api.user.rentals.models import Rental, RentalPackage
from api.user.stations.models import Station, StationSlot, PowerBank


class RentalStartMixin:
    """Mixin for rental start operations"""
    
    @transaction.atomic
    def start_rental(self, user, station_sn: str, package_id: str, powerbank_sn: Optional[str] = None) -> Rental:
        """
        Start a new rental session with device popup.
        
        Flow:
        1. Validate user and station
        2. Process payment (if PREPAID)
        3. Trigger device popup (sync, 15s timeout)
        4. If popup succeeds -> ACTIVE
        5. If popup times out -> PENDING_POPUP + async verification task
        6. If popup fails -> CANCELLED + refund
        
        Args:
            user: User starting rental
            station_sn: Station serial number
            package_id: Rental package ID
            powerbank_sn: Optional specific powerbank SN (if user selected from app)
        """
        try:
            self._validate_rental_prerequisites(user)
            
            station = Station.objects.get(serial_number=station_sn)
            package = RentalPackage.objects.get(id=package_id, is_active=True)
            
            self._validate_station_availability(station)
            
            if package.payment_model == 'POSTPAID':
                self._validate_postpaid_balance(user)
            
            # Get powerbank from DB for validation (will be confirmed by device)
            power_bank, slot = self._get_available_power_bank_and_slot(station)
            
            # Check for applicable discount
            discount = None
            actual_price = package.price
            discount_amount = Decimal('0')
            try:
                from api.user.promotions.services import DiscountService
                discount = DiscountService.get_applicable_discount(station_sn, package_id, user)
                
                if discount:
                    discount_amount, actual_price = DiscountService.calculate_discounted_price(
                        package.price, discount.discount_percent
                    )
                    self.log_info(
                        f"Discount applied: {discount.discount_percent}% off, "
                        f"original: {package.price}, final: {actual_price}"
                    )
            except Exception as e:
                self.log_warning(f"Failed to check discount: {e}. Continuing with original price.")
                discount = None
            
            # Create rental in PENDING_POPUP status
            rental = Rental.objects.create(
                user=user,
                station=station,
                slot=slot,
                package=package,
                power_bank=power_bank,
                rental_code=generate_rental_code(),
                status='PENDING_POPUP',
                due_at=timezone.now() + timezone.timedelta(minutes=package.duration_minutes),
                amount_paid=Decimal('0')
                ,
                rental_metadata={'discount': {
                    'discount_id': str(discount.id),
                    'original_price': str(package.price),
                    'discount_percent': str(discount.discount_percent),
                    'discount_amount': str(discount_amount),
                    'final_price': str(actual_price)
                }} if discount else {}
            )
            
            # Process prepayment before popup
            if package.payment_model == 'PREPAID':
                self._process_prepayment(user, package, rental, actual_price)
                rental.amount_paid = actual_price
                rental.payment_status = 'PAID'
                rental.save(update_fields=['amount_paid', 'payment_status'])
            
            # Trigger device popup
            popup_success, popup_result_sn = self._trigger_device_popup(
                rental, station, power_bank, powerbank_sn
            )
            
            if popup_success:
                # Popup successful - activate rental.
                # IMPORTANT: device returns the actual dispensed powerbank serial.
                # We must align Rental.power_bank with that serial, otherwise return events
                # (which identify by power_bank_serial) won't be able to complete the rental.
                if not popup_result_sn:
                    raise ServiceException(
                        detail="Device popup succeeded but returned no powerbank serial",
                        code="popup_sn_missing",
                    )

                # Lock and fetch the actual dispensed powerbank by serial
                actual_power_bank = PowerBank.objects.select_for_update().filter(
                    serial_number=popup_result_sn,
                ).first()

                if not actual_power_bank:
                    raise ServiceException(
                        detail=f"PowerBank with serial {popup_result_sn} not found",
                        code="powerbank_not_found",
                    )

                # Validate station relationship (must belong to same station at the time of popup)
                if actual_power_bank.current_station_id and actual_power_bank.current_station_id != station.id:
                    raise ServiceException(
                        detail="PowerBank does not belong to the requested station",
                        code="powerbank_station_mismatch",
                    )

                # Keep rental.slot consistent with the actual dispensed powerbank's slot (if known)
                if actual_power_bank.current_slot_id:
                    rental.slot = actual_power_bank.current_slot

                rental.power_bank = actual_power_bank

                from api.user.stations.services import PowerBankService
                powerbank_service = PowerBankService()
                powerbank_service.assign_power_bank_to_rental(actual_power_bank, rental)

                rental.status = 'ACTIVE'
                rental.started_at = timezone.now()
                rental.rental_metadata['popup_sn'] = popup_result_sn
                rental.save(update_fields=['status', 'started_at', 'rental_metadata', 'power_bank', 'slot'])
                
                # Record discount usage after successful activation
                if discount:
                    try:
                        from api.user.promotions.services import DiscountService
                        DiscountService.apply_discount(discount, user, rental, package.price)
                        self.log_info(f"Discount usage recorded for rental {rental.rental_code}")
                        
                        # Send discount notification
                        self._send_discount_notification(user, rental, discount, package.price, actual_price)
                    except Exception as e:
                        self.log_warning(f"Failed to record discount usage: {e}")

                self._schedule_reminder_notification(user, rental)
                self._send_rental_started_notification(user, actual_power_bank, station)

                self.log_info(f"Rental started: {rental.rental_code} by {user.username}")
            else:
                # Popup failed or timed out - rental stays in PENDING_POPUP
                # Async task will verify and update status
                self.log_warning(f"Rental {rental.rental_code} popup pending verification")
            
            return rental
            
        except Exception as e:
            self.handle_service_error(e, "Failed to start rental")
    
    def _trigger_device_popup(
        self, 
        rental: Rental, 
        station: Station, 
        power_bank: PowerBank,
        specific_sn: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Trigger device popup and handle result.
        
        Returns:
            Tuple[success, powerbank_sn]
        """
        from api.user.stations.services.device_api_service import get_device_api_service
        from api.user.stations.tasks import verify_popup_completion
        
        device_service = get_device_api_service()
        
        try:
            if specific_sn:
                # User selected specific powerbank
                success, result, message = device_service.popup_specific(
                    station.serial_number, specific_sn
                )
                powerbank_sn = result.powerbank_sn if result else None
            else:
                # Random popup
                success, powerbank_sn, message = device_service.popup_random(
                    station.serial_number,
                    min_power=20
                )
            
            if success:
                return True, powerbank_sn
            else:
                # Popup failed - schedule async verification
                rental.rental_metadata['popup_message'] = message
                rental.save(update_fields=['rental_metadata'])
                
                verify_popup_completion.apply_async(
                    args=[str(rental.id), station.serial_number, power_bank.serial_number],
                    countdown=10
                )
                return False, None
                
        except Exception as e:
            # Timeout or error - schedule async verification
            self.log_error(f"Device popup error for rental {rental.rental_code}: {e}")
            rental.rental_metadata['popup_error'] = str(e)
            rental.save(update_fields=['rental_metadata'])
            
            verify_popup_completion.apply_async(
                args=[str(rental.id), station.serial_number, power_bank.serial_number],
                countdown=10
            )
            return False, None
    
    def _validate_rental_prerequisites(self, user) -> None:
        """Validate user can start rental"""
        permission = CanRentPowerBank()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        mock_request = MockRequest(user)
        
        if not permission.has_permission(mock_request, None):
            raise ServiceException(
                detail="User does not meet rental requirements",
                code="rental_prerequisites_not_met"
            )
        
        active_rental = Rental.objects.filter(
            user=user,
            status__in=['PENDING', 'PENDING_POPUP', 'ACTIVE', 'OVERDUE']
        ).first()
        
        if active_rental:
            raise ServiceException(
                detail="You already have an active rental" if active_rental.status != 'OVERDUE' 
                       else "You have an overdue rental. Please clear payment first.",
                code="active_rental_exists"
            )
    
    def _validate_station_availability(self, station: Station) -> None:
        """Validate station is available for rental"""
        if station.status != 'ONLINE':
            raise ServiceException(detail="Station is not online", code="station_offline")
        
        if station.is_maintenance:
            raise ServiceException(detail="Station is under maintenance", code="station_maintenance")
    
    def _validate_postpaid_balance(self, user) -> None:
        """Validate user has minimum balance for POSTPAID rentals"""
        from api.user.system.models import AppConfig
        
        min_balance = Decimal(AppConfig.objects.filter(
            key='POSTPAID_MINIMUM_BALANCE', is_active=True
        ).values_list('value', flat=True).first() or '50')
        
        wallet_balance = Decimal('0')
        if hasattr(user, 'wallet') and user.wallet:
            wallet_balance = user.wallet.balance
        
        if wallet_balance < min_balance:
            raise ServiceException(
                detail=f"POSTPAID rentals require minimum wallet balance of NPR {min_balance}. Your balance: NPR {wallet_balance}.",
                code="insufficient_postpaid_balance"
            )
        
        self.log_info(f"POSTPAID balance check passed for user {user.username}")
    
    def _get_available_power_bank_and_slot(self, station: Station) -> Tuple[PowerBank, StationSlot]:
        """Get available power bank and slot from station with row-level locking"""
        # Find powerbank that is available with sufficient battery
        power_bank = PowerBank.objects.select_for_update().filter(
            current_station=station,
            status='AVAILABLE',
            battery_level__gte=20,
            current_slot__isnull=False
        ).order_by('-battery_level').first()
        
        if not power_bank:
            raise ServiceException(detail="No power bank available with sufficient battery", code="no_power_bank_available")
        
        # Get the slot where this powerbank is located
        slot = power_bank.current_slot
        
        if not slot or slot.status == 'MAINTENANCE':
            raise ServiceException(detail="Slot is not available", code="slot_not_available")
        
        return power_bank, slot
    
    def _process_prepayment(self, user, package: RentalPackage, rental=None, amount: Decimal = None):
        """Process pre-payment for rental"""
        from api.user.payments.services import PaymentCalculationService, RentalPaymentService
        
        payment_amount = amount if amount is not None else package.price

        calc_service = PaymentCalculationService()
        payment_options = calc_service.calculate_payment_options(
            user=user,
            scenario='pre_payment',
            package_id=str(package.id),
            amount=payment_amount
        )
        
        if not payment_options['is_sufficient']:
            raise ServiceException(
                detail=f"Insufficient balance. Need NPR {payment_options['shortfall']} more.",
                code="insufficient_balance"
            )
        
        payment_service = RentalPaymentService()
        return payment_service.process_rental_payment(
            user=user,
            rental=rental,
            payment_breakdown=payment_options['payment_breakdown']
        )
