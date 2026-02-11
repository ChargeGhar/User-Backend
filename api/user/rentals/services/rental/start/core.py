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
from .payment import process_prepayment, create_postpaid_transaction
from .device import trigger_device_popup, activate_rental_powerbank
from .discount import (
    get_applicable_discount,
    build_discount_metadata,
    record_discount_usage,
)
from .vendor_ejection import check_vendor_free_ejection, log_vendor_free_ejection
from .revenue import trigger_revenue_distribution


class RentalStartMixin:
    """Mixin for rental start operations."""
    
    def start_rental(
        self,
        user,
        station_sn: str,
        package_id: str,
        powerbank_sn: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        pricing_override: Optional[dict] = None,
        payment_mode: str = 'wallet_points',
        wallet_amount: Optional[Decimal] = None,
        points_to_use: Optional[int] = None
    ) -> Rental:
        """
        Start a new rental session with device popup.
        
        Flow:
        1. Validate user and station
        2. Get discount if applicable
        3. Validate payment (may raise payment_required)
        4. Create rental in PENDING_POPUP status
        5. Process payment (if PREPAID)
        6. Trigger device popup (sync, 15s timeout)
        7. If popup succeeds -> ACTIVE + revenue distribution
        8. If popup times out -> PENDING_POPUP + async verification
        """
        try:
            # Step 1: Validation
            validate_rental_prerequisites(user)
            station = Station.objects.get(serial_number=station_sn)
            package = RentalPackage.objects.get(id=package_id, is_active=True)
            validate_station_availability(station)

            # Step 2: Resolve pricing
            discount, discount_amount, actual_price, rental_metadata = self._resolve_pricing(
                station_sn, package, user, pricing_override
            )

            # Step 3: Payment validation (may raise payment_required exception)
            payment_mode = payment_mode or 'wallet_points'
            self._validate_and_check_payment(
                user, package, actual_price, payment_mode, payment_method_id,
                station_sn, package_id, powerbank_sn, discount, discount_amount,
                rental_metadata, wallet_amount, points_to_use
            )

            # Step 4: Create rental atomically
            return self._start_rental_atomic(
                user, station, package, powerbank_sn, discount, discount_amount,
                actual_price, rental_metadata, payment_mode, wallet_amount, points_to_use
            )

        except Exception as e:
            if isinstance(e, ServiceException):
                raise
            self.handle_service_error(e, "Failed to start rental")

    def _resolve_pricing(self, station_sn: str, package: RentalPackage, user, pricing_override: Optional[dict]):
        """Resolve discount and actual price from override or fresh calculation."""
        if pricing_override and pricing_override.get('actual_price') is not None:
            actual_price = Decimal(str(pricing_override['actual_price']))
            discount_metadata = pricing_override.get('discount_metadata') or {}
            discount_amount_raw = pricing_override.get('discount_amount') or discount_metadata.get('discount', {}).get('discount_amount', '0')
            discount_amount = Decimal(str(discount_amount_raw))

            discount = None
            if pricing_override.get('discount_id'):
                try:
                    from api.user.promotions.models import Discount
                    discount = Discount.objects.get(id=pricing_override['discount_id'])
                except Exception:
                    pass

            return discount, discount_amount, actual_price, discount_metadata

        discount, discount_amount, actual_price = get_applicable_discount(station_sn, str(package.id), user)
        
        if discount:
            self.log_info(f"Discount applied: {discount.discount_percent}% off, original: {package.price}, final: {actual_price}")

        return discount, discount_amount, actual_price, build_discount_metadata(discount, package.price, discount_amount, actual_price)

    def _validate_and_check_payment(
        self, user, package, actual_price, payment_mode, payment_method_id,
        station_sn, package_id, powerbank_sn, discount, discount_amount,
        rental_metadata, wallet_amount, points_to_use
    ):
        """Validate payment requirements and raise payment_required if needed."""
        from api.user.payments.services import RentalPaymentFlowService
        flow_service = RentalPaymentFlowService()

        # Direct mode: always require top-up
        if payment_mode == 'direct':
            if package.payment_model == 'POSTPAID':
                from api.user.system.services import AppConfigService

                min_balance = Decimal(
                    str(AppConfigService().get_config_cached('POSTPAID_MINIMUM_BALANCE', '50'))
                )
                wallet_balance = (
                    user.wallet.balance if hasattr(user, 'wallet') and user.wallet else Decimal('0')
                )
                required_amount = max(
                    Decimal('0.00'),
                    (min_balance - wallet_balance).quantize(Decimal('0.01'))
                )

                # If POSTPAID minimum is already satisfied, continue without forcing gateway.
                if required_amount <= 0:
                    return

                topup_amount = required_amount
                postpaid_min_balance = min_balance
            else:
                # PREPAID direct mode: top-up exactly the discounted payable amount.
                topup_amount = actual_price.quantize(Decimal('0.01'))
                postpaid_min_balance = None

            self._raise_payment_required(
                flow_service, user, payment_method_id, topup_amount, 
                station_sn, package_id, powerbank_sn, actual_price,
                discount, discount_amount, rental_metadata, package.payment_model,
                payment_mode, 'wallet', None, None,
                postpaid_min_balance=postpaid_min_balance
            )

        # PREPAID: check wallet/points sufficiency
        if package.payment_model == 'PREPAID':
            payment_options = flow_service.calculate_payment_options(
                user=user,
                scenario='pre_payment',
                package_id=str(package.id),
                amount=actual_price,
                payment_mode=payment_mode,
                wallet_amount=wallet_amount,
                points_to_use=points_to_use,
            )

            if not payment_options['is_sufficient']:
                topup_amount = Decimal(str(payment_options.get('topup_amount_required') or payment_options.get('shortfall') or actual_price))
                resume_mode, resume_wallet, resume_points = self._get_resume_preferences(
                    payment_mode, wallet_amount, points_to_use, payment_options
                )

                self._raise_payment_required(
                    flow_service, user, payment_method_id, topup_amount,
                    station_sn, package_id, powerbank_sn, actual_price,
                    discount, discount_amount, rental_metadata, package.payment_model,
                    payment_mode, resume_mode, resume_wallet, resume_points,
                    payment_options
                )

        # POSTPAID: validate payment mode and minimum balance
        else:
            if payment_mode in {'points', 'wallet_points'}:
                raise ServiceException(
                    detail=f"Payment mode '{payment_mode}' is not supported for POSTPAID packages",
                    code="payment_mode_not_supported",
                    context={'payment_mode': payment_mode, 'payment_model': package.payment_model}
                )

            from api.user.system.services import AppConfigService
            min_balance = Decimal(str(AppConfigService().get_config_cached('POSTPAID_MINIMUM_BALANCE', '50')))
            wallet_balance = user.wallet.balance if hasattr(user, 'wallet') and user.wallet else Decimal('0')

            if wallet_balance < min_balance:
                required_amount = min_balance - wallet_balance
                self._raise_payment_required(
                    flow_service, user, payment_method_id, required_amount,
                    station_sn, package_id, powerbank_sn, actual_price,
                    discount, discount_amount, rental_metadata, package.payment_model,
                    payment_mode, self._get_resume_mode(payment_mode), wallet_amount, points_to_use,
                    postpaid_min_balance=min_balance
                )

    def _raise_payment_required(
        self, flow_service, user, payment_method_id, topup_amount,
        station_sn, package_id, powerbank_sn, actual_price,
        discount, discount_amount, rental_metadata, payment_model,
        requested_mode, resume_mode, resume_wallet, resume_points,
        payment_options=None, postpaid_min_balance=None
    ):
        """Create payment intent and raise payment_required exception."""
        if not payment_method_id:
            raise ServiceException(
                detail="Payment method is required when balance is insufficient",
                code="payment_method_required",
                context={'payment_mode': requested_mode, 'shortfall': str(topup_amount)}
            )

        gateway_topup_amount = flow_service.resolve_gateway_topup_amount(
            payment_method_id=payment_method_id,
            requested_amount=topup_amount,
        )

        metadata = {
            'flow': 'RENTAL_START',
            'station_sn': station_sn,
            'package_id': str(package_id),
            'powerbank_sn': powerbank_sn,
            'actual_price': str(actual_price),
            'discount_id': str(discount.id) if discount else None,
            'discount_amount': str(discount_amount),
            'discount_metadata': rental_metadata,
            'payment_model': payment_model,
            'payment_mode_requested': requested_mode,
            'payment_mode': resume_mode,
            'wallet_amount': str(resume_wallet) if resume_wallet is not None else None,
            'points_to_use': resume_points,
            'topup_amount_required': str(gateway_topup_amount),
            'shortfall': str(topup_amount)
        }

        if payment_options:
            metadata['payment_breakdown'] = flow_service.serialize_for_metadata(payment_options.get('payment_breakdown'))
            metadata['shortfall'] = str(payment_options.get('shortfall', topup_amount))
        
        if postpaid_min_balance:
            metadata['postpaid_min_balance'] = str(postpaid_min_balance)

        intent = flow_service.create_topup_intent(
            user, payment_method_id, gateway_topup_amount, metadata
        )

        raise ServiceException(
            detail="Payment required to start rental",
            code="payment_required",
            status_code=402,
            context=flow_service.build_payment_required_context(
                intent, topup_amount if not payment_options else payment_options.get('shortfall'),
                requested_mode, payment_options
            )
        )

    def _get_resume_mode(self, payment_mode: str) -> str:
        """Determine resume mode after gateway top-up."""
        return 'wallet' if payment_mode == 'direct' else ('wallet_points' if payment_mode == 'points' else payment_mode)

    def _get_resume_preferences(self, selected_mode, wallet_amount, points_to_use, payment_options):
        """Build deterministic resume preferences for async rental continuation."""
        resume_mode = self._get_resume_mode(selected_mode)
        resume_wallet = wallet_amount
        resume_points = points_to_use

        # Clear requested split if points are short (gateway can't add points)
        if selected_mode == 'wallet_points' and wallet_amount is not None and points_to_use is not None:
            if int(payment_options.get('points_shortfall', 0) or 0) > 0:
                resume_wallet = None
                resume_points = None

        return resume_mode, resume_wallet, resume_points

    @transaction.atomic
    def _start_rental_atomic(
        self, user, station, package, powerbank_sn, discount, discount_amount,
        actual_price, rental_metadata, payment_mode, wallet_amount, points_to_use
    ) -> Rental:
        """Atomic rental creation and popup flow."""
        # Re-validate inside transaction
        validate_rental_prerequisites(user)
        validate_station_availability(station)
        
        if package.payment_model == 'POSTPAID':
            validate_postpaid_balance(user)

        power_bank, slot = get_available_power_bank_and_slot(station)

        # Build metadata
        runtime_metadata = dict(rental_metadata or {})
        runtime_metadata['payment_mode'] = payment_mode
        if wallet_amount is not None:
            runtime_metadata['wallet_amount_requested'] = str(wallet_amount)
        if points_to_use is not None:
            runtime_metadata['points_to_use_requested'] = int(points_to_use)

        # Create rental
        rental = Rental.objects.create(
            user=user, station=station, slot=slot, package=package,
            power_bank=power_bank, rental_code=generate_rental_code(),
            status='PENDING_POPUP',
            due_at=timezone.now() + timezone.timedelta(minutes=package.duration_minutes),
            amount_paid=Decimal('0'), rental_metadata=runtime_metadata
        )

        # Process payment
        if package.payment_model == 'PREPAID':
            process_prepayment(user, package, rental, actual_price, payment_mode, wallet_amount, points_to_use)
            rental.amount_paid = actual_price
            rental.payment_status = 'PAID'
            rental.save(update_fields=['amount_paid', 'payment_status'])
        else:
            txn = create_postpaid_transaction(user, rental, actual_price)
            rental.rental_metadata['pending_transaction_id'] = str(txn.id)
            rental.save(update_fields=['rental_metadata'])

        # Trigger device popup
        popup_success, popup_result_sn = trigger_device_popup(rental, station, power_bank, powerbank_sn)

        if popup_success:
            self._handle_popup_success(rental, station, package, user, popup_result_sn, discount, actual_price)
        else:
            self.log_warning(f"Rental {rental.rental_code} popup pending verification")

        return rental
    
    def _handle_popup_success(self, rental, station, package, user, popup_result_sn, discount, actual_price):
        """Handle successful popup - activate rental and trigger post-activation tasks."""
        actual_power_bank = validate_powerbank_for_rental(rental.power_bank, station, popup_result_sn)
        
        # Update rental with actual powerbank/slot
        if actual_power_bank.current_slot_id:
            rental.slot = actual_power_bank.current_slot
        rental.power_bank = actual_power_bank
        rental.start_battery_level = actual_power_bank.battery_level
        rental.save(update_fields=['power_bank', 'slot', 'start_battery_level'])
        
        # Assign powerbank and activate
        activate_rental_powerbank(rental, actual_power_bank)
        started_at = timezone.now()
        rental.status = 'ACTIVE'
        rental.started_at = started_at
        rental.due_at = started_at + timezone.timedelta(minutes=package.duration_minutes)
        rental.rental_metadata['popup_sn'] = popup_result_sn
        rental.save(update_fields=['status', 'started_at', 'due_at', 'rental_metadata'])
        
        # Post-activation tasks
        if discount:
            record_discount_usage(discount, user, rental, package.price)
            self._send_discount_notification(user, rental, discount, package.price, actual_price)
        
        if check_vendor_free_ejection(user, station):
            log_vendor_free_ejection(user, station, rental, actual_power_bank)
            self.log_info(f"Vendor free ejection logged for rental {rental.rental_code}")
        
        if package.payment_model == 'PREPAID':
            trigger_revenue_distribution(rental)
        
        self._schedule_reminder_notification(user, rental)
        self._send_rental_started_notification(user, actual_power_bank, station)
        self.log_info(f"Rental started: {rental.rental_code} by {user.username}")
