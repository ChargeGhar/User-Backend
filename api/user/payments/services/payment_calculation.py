from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from typing import Any, Dict

from api.common.services.base import BaseService, ServiceException
from api.common.utils.helpers import convert_points_to_amount
from api.user.points.models import UserPoints


class PaymentCalculationService(BaseService):
    """Service for payment calculations."""

    PAYMENT_MODE_CHOICES = {'wallet', 'points', 'wallet_points', 'direct'}
    CURRENCY_QUANTIZE = Decimal('0.01')
    POINTS_PER_NPR = Decimal('10')

    def calculate_payment_options(self, user, scenario: str, **kwargs) -> Dict[str, Any]:
        """
        Calculate payment options for rental scenarios.

        Scenarios:
        - pre_payment: package pre-check and payment split
        - post_payment: due settlement and payment split

        Payment modes:
        - wallet
        - points
        - wallet_points
        - direct (always requires gateway top-up)
        """
        try:
            package_id = kwargs.get('package_id')
            rental_id = kwargs.get('rental_id')
            payment_mode = kwargs.get('payment_mode') or 'wallet_points'
            wallet_amount = kwargs.get('wallet_amount')
            points_to_use = kwargs.get('points_to_use')
            self._validate_payment_mode_inputs(payment_mode, wallet_amount, points_to_use)

            # Determine payable amount based on scenario
            if scenario == 'pre_payment':
                if not package_id:
                    raise ServiceException(
                        detail="Package ID required for pre-payment calculation",
                        code="package_required"
                    )
                from api.user.rentals.models import RentalPackage

                package = RentalPackage.objects.get(id=package_id, is_active=True)
                amount_override = kwargs.get('amount')
                amount = Decimal(str(amount_override)) if amount_override is not None else package.price
                amount = self._quantize_currency(amount)

                if package.payment_model != 'PREPAID':
                    raise ServiceException(
                        detail=(
                            f"Package '{package.name}' uses {package.payment_model} model, "
                            f"not suitable for pre-payment calculation"
                        ),
                        code="invalid_package_payment_model"
                    )

            elif scenario == 'post_payment':
                if not rental_id:
                    raise ServiceException(
                        detail="Rental ID required for post-payment calculation",
                        code="rental_required"
                    )
                from api.user.rentals.models import Rental

                rental = Rental.objects.get(id=rental_id, user=user)
                if rental.package.payment_model == 'POSTPAID':
                    if rental.ended_at and rental.started_at:
                        usage_duration = rental.ended_at - rental.started_at
                        usage_minutes = int(usage_duration.total_seconds() / 60)
                        package_rate_per_minute = rental.package.price / rental.package.duration_minutes
                        amount = Decimal(str(usage_minutes)) * package_rate_per_minute

                        if rental.ended_at > rental.due_at:
                            from api.common.utils.helpers import calculate_late_fee_amount, calculate_overdue_minutes

                            overdue_minutes = calculate_overdue_minutes(rental)
                            if overdue_minutes > 0:
                                late_fee = calculate_late_fee_amount(package_rate_per_minute, overdue_minutes)
                                amount += late_fee

                                from api.user.notifications.services import notify

                                notify(
                                    user,
                                    'fines_dues',
                                    async_send=True,
                                    amount=float(late_fee),
                                    reason=f"Late return penalty - {overdue_minutes} minutes overdue"
                                )
                        else:
                            amount = rental.package.price
                    else:
                        amount = rental.package.price
                else:
                    amount = rental.overdue_amount or rental.package.price
                amount = self._quantize_currency(amount)
            else:
                raise ServiceException(
                    detail="Invalid scenario. Supported scenarios: pre_payment, post_payment",
                    code="invalid_scenario"
                )

            user_points = self._get_user_points(user)
            wallet_balance = self._quantize_currency(self._get_wallet_balance(user))
            points_value = self._quantize_currency(convert_points_to_amount(user_points))

            if payment_mode == 'direct':
                payment_breakdown = {
                    'points_to_use': 0,
                    'points_amount': Decimal('0.00'),
                    'wallet_amount': Decimal('0.00'),
                    'direct_amount': amount,
                    'requested_split': None,
                }
                is_sufficient = False
                shortfall = amount
                wallet_shortfall = amount
                points_shortfall = 0
                points_shortfall_amount = Decimal('0.00')
                total_available_for_mode = Decimal('0.00')
            else:
                payment_breakdown = self._calculate_payment_breakdown(
                    amount=amount,
                    user_points=user_points,
                    wallet_balance=wallet_balance,
                    payment_mode=payment_mode,
                    wallet_amount=wallet_amount,
                    points_to_use=points_to_use
                )
                is_sufficient = payment_breakdown['is_sufficient']
                shortfall = payment_breakdown['shortfall']
                wallet_shortfall = payment_breakdown['wallet_shortfall']
                points_shortfall = payment_breakdown['points_shortfall']
                points_shortfall_amount = payment_breakdown['points_shortfall_amount']

                if payment_mode == 'wallet':
                    total_available_for_mode = wallet_balance
                elif payment_mode == 'points':
                    total_available_for_mode = points_value
                else:
                    total_available_for_mode = points_value + wallet_balance

            suggested_topup = None
            if shortfall > 0:
                suggested_topup = ((shortfall // 100) + 1) * 100

            points_used = payment_breakdown['points_to_use']
            points_amount = self._quantize_currency(payment_breakdown['points_amount'])
            wallet_used = self._quantize_currency(payment_breakdown['wallet_amount'])
            direct_amount = self._quantize_currency(payment_breakdown.get('direct_amount', Decimal('0.00')))

            remaining_points = max(0, user_points - points_used)
            remaining_wallet = self._quantize_currency(max(Decimal('0.00'), wallet_balance - wallet_used))

            return {
                'scenario': scenario,
                'payment_mode': payment_mode,
                'total_amount': amount,
                'user_balances': {
                    'points': user_points,
                    'wallet': wallet_balance,
                    'points_value': points_value,
                    'points_to_npr_rate': 10.0,  # 10 points = NPR 1
                    'total_available': self._quantize_currency(points_value + wallet_balance),
                    'total_available_for_mode': self._quantize_currency(total_available_for_mode),
                },
                'payment_breakdown': {
                    # Backward-compatible keys
                    'points_used': points_used,
                    'wallet_used': wallet_used,
                    # Canonical keys
                    'points_to_use': points_used,
                    'points_amount': points_amount,
                    'wallet_amount': wallet_used,
                    'direct_amount': direct_amount,
                    'requested_split': payment_breakdown.get('requested_split'),
                    'remaining_balance': {
                        'points': remaining_points,
                        'wallet': remaining_wallet
                    }
                },
                'is_sufficient': is_sufficient,
                'shortfall': self._quantize_currency(shortfall),
                'wallet_shortfall': self._quantize_currency(wallet_shortfall),
                'points_shortfall': points_shortfall,
                'points_shortfall_amount': self._quantize_currency(points_shortfall_amount),
                'topup_amount_required': self._quantize_currency(shortfall),
                'suggested_topup': suggested_topup,
                'wallet_topup_note': 'If insufficient funds, use /api/payments/wallet/topup-intent to add money to wallet'
            }

        except Exception as e:
            self.handle_service_error(e, "Failed to calculate payment options")

    def calculate_package_payment_options(self, user, package_id: str) -> Dict[str, Any]:
        """
        Calculate payment options for a specific rental package.

        Automatically determines scenario based on package.payment_model.
        """
        try:
            from api.user.rentals.models import RentalPackage

            package = RentalPackage.objects.get(id=package_id, is_active=True)
            scenario = 'pre_payment'
            return self.calculate_payment_options(
                user=user,
                scenario=scenario,
                package_id=package_id
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to calculate package payment options")

    def _validate_payment_mode_inputs(self, payment_mode: str, wallet_amount, points_to_use) -> None:
        if payment_mode not in self.PAYMENT_MODE_CHOICES:
            raise ServiceException(
                detail=f"Invalid payment mode. Supported: {', '.join(sorted(self.PAYMENT_MODE_CHOICES))}",
                code="invalid_payment_mode"
            )

        has_wallet = wallet_amount is not None
        has_points = points_to_use is not None
        if has_wallet ^ has_points:
            raise ServiceException(
                detail="Provide both wallet_amount and points_to_use together",
                code="invalid_wallet_points_split"
            )

        if payment_mode != 'wallet_points' and (has_wallet or has_points):
            raise ServiceException(
                detail="wallet_amount and points_to_use are only valid for wallet_points mode",
                code="invalid_wallet_points_split"
            )

    def _quantize_currency(self, amount: Decimal) -> Decimal:
        return Decimal(str(amount)).quantize(self.CURRENCY_QUANTIZE)

    def _amount_to_points_floor(self, amount: Decimal) -> int:
        normalized = self._quantize_currency(amount)
        return int((normalized * self.POINTS_PER_NPR).to_integral_value(rounding=ROUND_FLOOR))

    def _amount_to_points_ceil(self, amount: Decimal) -> int:
        normalized = self._quantize_currency(amount)
        return int((normalized * self.POINTS_PER_NPR).to_integral_value(rounding=ROUND_CEILING))

    def _calculate_payment_breakdown(
        self,
        amount: Decimal,
        user_points: int,
        wallet_balance: Decimal,
        payment_mode: str,
        wallet_amount,
        points_to_use
    ) -> Dict[str, Any]:
        points_to_use_applied = 0
        points_amount = Decimal('0.00')
        wallet_amount_applied = Decimal('0.00')
        requested_split = None
        wallet_shortfall = Decimal('0.00')
        points_shortfall = 0
        points_shortfall_amount = Decimal('0.00')

        if payment_mode == 'wallet':
            wallet_amount_applied = min(wallet_balance, amount)
            shortfall = max(Decimal('0.00'), amount - wallet_balance)
            is_sufficient = wallet_balance >= amount
            wallet_shortfall = shortfall

        elif payment_mode == 'points':
            points_target_floor = self._amount_to_points_floor(amount)
            points_to_use_applied = min(user_points, points_target_floor)
            points_amount = self._quantize_currency(convert_points_to_amount(points_to_use_applied))
            shortfall = max(Decimal('0.00'), amount - points_amount)
            is_sufficient = shortfall == Decimal('0.00')
            points_target_ceil = self._amount_to_points_ceil(amount)
            points_shortfall = max(0, points_target_ceil - user_points)
            points_shortfall_amount = self._quantize_currency(convert_points_to_amount(points_shortfall))
            wallet_shortfall = shortfall

        elif payment_mode == 'wallet_points':
            if wallet_amount is not None and points_to_use is not None:
                try:
                    requested_wallet_amount = self._quantize_currency(Decimal(str(wallet_amount)))
                    requested_points = int(points_to_use)
                except (InvalidOperation, TypeError, ValueError):
                    raise ServiceException(
                        detail="Invalid wallet_amount or points_to_use value",
                        code="invalid_wallet_points_split"
                    )

                if requested_wallet_amount < 0 or requested_points < 0:
                    raise ServiceException(
                        detail="wallet_amount and points_to_use must be non-negative",
                        code="invalid_wallet_points_split"
                    )

                requested_points_amount = self._quantize_currency(convert_points_to_amount(requested_points))
                requested_total = self._quantize_currency(requested_wallet_amount + requested_points_amount)
                if requested_total != amount:
                    raise ServiceException(
                        detail="wallet_amount and points_to_use must exactly match the payable amount",
                        code="split_total_mismatch",
                        context={
                            'requested_total': str(requested_total),
                            'expected_total': str(amount)
                        }
                    )

                requested_split = {
                    'wallet_amount': requested_wallet_amount,
                    'points_to_use': requested_points,
                    'points_amount': requested_points_amount
                }

                wallet_amount_applied = min(wallet_balance, requested_wallet_amount)
                points_to_use_applied = min(user_points, requested_points)
                points_amount = self._quantize_currency(convert_points_to_amount(points_to_use_applied))

                wallet_shortfall = max(Decimal('0.00'), requested_wallet_amount - wallet_balance)
                points_shortfall = max(0, requested_points - user_points)
                points_shortfall_amount = self._quantize_currency(convert_points_to_amount(points_shortfall))
                shortfall = self._quantize_currency(wallet_shortfall + points_shortfall_amount)
                is_sufficient = wallet_shortfall == 0 and points_shortfall == 0
            else:
                points_to_use_applied = min(user_points, self._amount_to_points_floor(amount))
                points_amount = self._quantize_currency(convert_points_to_amount(points_to_use_applied))
                wallet_amount_applied = max(Decimal('0.00'), amount - points_amount)
                shortfall = max(Decimal('0.00'), wallet_amount_applied - wallet_balance)
                is_sufficient = shortfall == Decimal('0.00')
                wallet_shortfall = max(Decimal('0.00'), wallet_amount_applied - wallet_balance)
                points_shortfall = 0
                points_shortfall_amount = Decimal('0.00')
        else:
            raise ServiceException(
                detail=f"Unsupported payment mode: {payment_mode}",
                code="invalid_payment_mode"
            )

        return {
            'points_to_use': points_to_use_applied,
            'points_amount': self._quantize_currency(points_amount),
            'wallet_amount': self._quantize_currency(wallet_amount_applied),
            'direct_amount': Decimal('0.00'),
            'requested_split': requested_split,
            'is_sufficient': is_sufficient,
            'shortfall': self._quantize_currency(shortfall),
            'wallet_shortfall': self._quantize_currency(wallet_shortfall),
            'points_shortfall': points_shortfall,
            'points_shortfall_amount': self._quantize_currency(points_shortfall_amount),
            'total_amount': self._quantize_currency(points_amount + wallet_amount_applied),
        }

    def _get_user_points(self, user) -> int:
        """Get user's current points."""
        try:
            return user.points.current_points
        except UserPoints.DoesNotExist:
            return 0

    def _get_wallet_balance(self, user) -> Decimal:
        """Get user's wallet balance."""
        try:
            return user.wallet.balance
        except Exception:
            return Decimal('0')
