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
    
    def start_rental(
        self,
        user,
        station_sn: str,
        package_id: str,
        powerbank_sn: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        pricing_override: Optional[dict] = None
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
            payment_method_id: Optional payment method ID (required if payment is needed)
            pricing_override: Optional pricing override from payment intent (actual_price, discount info)
        
        Returns:
            Rental object
        """
        try:
            # Step 1: Validation (pre-check stage)
            validate_rental_prerequisites(user)

            station = Station.objects.get(serial_number=station_sn)
            package = RentalPackage.objects.get(id=package_id, is_active=True)

            validate_station_availability(station)

            discount, discount_amount, actual_price, rental_metadata = self._resolve_pricing(
                station_sn=station_sn,
                package=package,
                user=user,
                pricing_override=pricing_override
            )

            # Step 2: Payment pre-check (no locks)
            if package.payment_model == 'PREPAID':
                from api.user.payments.services import PaymentCalculationService
                calc_service = PaymentCalculationService()
                payment_options = calc_service.calculate_payment_options(
                    user=user,
                    scenario='pre_payment',
                    package_id=str(package.id),
                    amount=actual_price
                )

                if not payment_options['is_sufficient']:
                    if not payment_method_id:
                        raise ServiceException(
                            detail="Payment method is required when balance is insufficient",
                            code="payment_method_required"
                        )

                    intent = self._create_rental_topup_intent(
                        user=user,
                        payment_method_id=payment_method_id,
                        amount=actual_price,
                        metadata={
                            'flow': 'RENTAL_START',
                            'station_sn': station_sn,
                            'package_id': str(package.id),
                            'powerbank_sn': powerbank_sn,
                            'actual_price': str(actual_price),
                            'discount_id': str(discount.id) if discount else None,
                            'discount_amount': str(discount_amount),
                            'discount_metadata': rental_metadata,
                            'payment_model': package.payment_model
                        }
                    )

                    raise ServiceException(
                        detail="Payment required to start rental",
                        code="payment_required",
                        status_code=402,
                        context=self._build_payment_required_context(
                            intent=intent,
                            shortfall=payment_options.get('shortfall')
                        )
                    )
            else:
                # POSTPAID: Require minimum balance, otherwise trigger top-up
                from api.user.system.services import AppConfigService
                min_balance_str = AppConfigService().get_config_cached('POSTPAID_MINIMUM_BALANCE', '50')
                min_balance = Decimal(str(min_balance_str))

                wallet_balance = Decimal('0')
                if hasattr(user, 'wallet') and user.wallet:
                    wallet_balance = user.wallet.balance

                if wallet_balance < min_balance:
                    if not payment_method_id:
                        raise ServiceException(
                            detail="Payment method is required when balance is insufficient",
                            code="payment_method_required"
                        )

                    required_amount = min_balance - wallet_balance
                    intent = self._create_rental_topup_intent(
                        user=user,
                        payment_method_id=payment_method_id,
                        amount=required_amount,
                        metadata={
                            'flow': 'RENTAL_START',
                            'station_sn': station_sn,
                            'package_id': str(package.id),
                            'powerbank_sn': powerbank_sn,
                            'actual_price': str(actual_price),
                            'discount_id': str(discount.id) if discount else None,
                            'discount_amount': str(discount_amount),
                            'discount_metadata': rental_metadata,
                            'payment_model': package.payment_model,
                            'postpaid_min_balance': str(min_balance)
                        }
                    )

                    raise ServiceException(
                        detail="Payment required to meet minimum balance",
                        code="payment_required",
                        status_code=402,
                        context=self._build_payment_required_context(
                            intent=intent,
                            shortfall=required_amount
                        )
                    )

            return self._start_rental_atomic(
                user=user,
                station=station,
                package=package,
                powerbank_sn=powerbank_sn,
                discount=discount,
                discount_amount=discount_amount,
                actual_price=actual_price,
                rental_metadata=rental_metadata
            )

        except Exception as e:
            if isinstance(e, ServiceException):
                raise
            self.handle_service_error(e, "Failed to start rental")

    def _resolve_pricing(
        self,
        station_sn: str,
        package: RentalPackage,
        user,
        pricing_override: Optional[dict] = None
    ):
        """Resolve discount and actual price, optionally using override from payment intent."""
        if pricing_override and pricing_override.get('actual_price') is not None:
            actual_price = Decimal(str(pricing_override['actual_price']))
            discount_metadata = pricing_override.get('discount_metadata') or {}
            discount_amount_raw = pricing_override.get('discount_amount')

            if discount_amount_raw is None and discount_metadata.get('discount'):
                discount_amount_raw = discount_metadata['discount'].get('discount_amount', '0')

            discount_amount = Decimal(str(discount_amount_raw or '0'))

            discount = None
            discount_id = pricing_override.get('discount_id')
            if discount_id:
                try:
                    from api.user.promotions.models import Discount
                    discount = Discount.objects.get(id=discount_id)
                except Exception:
                    discount = None

            return discount, discount_amount, actual_price, discount_metadata

        discount, discount_amount, actual_price = get_applicable_discount(
            station_sn, str(package.id), user
        )

        if discount:
            self.log_info(
                f"Discount applied: {discount.discount_percent}% off, "
                f"original: {package.price}, final: {actual_price}"
            )

        rental_metadata = build_discount_metadata(
            discount, package.price, discount_amount, actual_price
        )

        return discount, discount_amount, actual_price, rental_metadata

    def _create_rental_topup_intent(self, user, payment_method_id: str, amount: Decimal, metadata: dict):
        """Create a top-up intent and attach rental start metadata."""
        from api.user.payments.services import PaymentIntentService

        intent_service = PaymentIntentService()
        intent = intent_service.create_topup_intent(
            user=user,
            amount=amount,
            payment_method_id=payment_method_id
        )

        intent.intent_metadata.update(metadata)
        intent.save(update_fields=['intent_metadata'])
        return intent

    def _build_payment_required_context(self, intent, shortfall: Optional[Decimal] = None) -> dict:
        gateway_result = intent.intent_metadata.get('gateway_result', {}) if intent.intent_metadata else {}
        return {
            'intent_id': intent.intent_id,
            'amount': str(intent.amount),
            'currency': intent.currency,
            'gateway': intent.intent_metadata.get('gateway') if intent.intent_metadata else None,
            'gateway_url': intent.gateway_url,
            'redirect_url': gateway_result.get('redirect_url'),
            'redirect_method': gateway_result.get('redirect_method', 'POST'),
            'form_fields': gateway_result.get('form_fields', {}),
            'payment_instructions': gateway_result.get('payment_instructions'),
            'expires_at': intent.expires_at.isoformat() if intent.expires_at else None,
            'status': intent.status,
            'shortfall': str(shortfall) if shortfall is not None else None
        }

    @transaction.atomic
    def _start_rental_atomic(
        self,
        user,
        station: Station,
        package: RentalPackage,
        powerbank_sn: Optional[str],
        discount,
        discount_amount: Decimal,
        actual_price: Decimal,
        rental_metadata: dict
    ) -> Rental:
        """Atomic rental creation and popup flow."""
        # Re-validate inside transaction for safety
        validate_rental_prerequisites(user)
        validate_station_availability(station)

        if package.payment_model == 'POSTPAID':
            validate_postpaid_balance(user)

        power_bank, slot = get_available_power_bank_and_slot(station)

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
            rental_metadata=rental_metadata or {}
        )

        # Process payment (PREPAID only)
        if package.payment_model == 'PREPAID':
            process_prepayment(user, package, rental, actual_price)
            rental.amount_paid = actual_price
            rental.payment_status = 'PAID'
            rental.save(update_fields=['amount_paid', 'payment_status'])
        else:
            # Create PENDING transaction for POSTPAID
            from .payment import create_postpaid_transaction
            transaction = create_postpaid_transaction(user, rental, actual_price)
            rental.rental_metadata['pending_transaction_id'] = str(transaction.id)
            rental.save(update_fields=['rental_metadata'])

        # Trigger device popup
        popup_success, popup_result_sn = trigger_device_popup(
            rental, station, power_bank, powerbank_sn
        )

        # Handle popup result
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

        # Capture start battery level
        rental.start_battery_level = actual_power_bank.battery_level
        rental.save(update_fields=['power_bank', 'slot', 'start_battery_level'])
        
        # Assign powerbank to rental
        activate_rental_powerbank(rental, actual_power_bank)
        
        # Activate rental
        rental.status = 'ACTIVE'
        rental.started_at = timezone.now()
        rental.rental_metadata['popup_sn'] = popup_result_sn
        rental.save(update_fields=['status', 'started_at', 'rental_metadata'])
        
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
