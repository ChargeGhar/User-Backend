from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from typing import Any, Dict

from api.common.services.base import BaseService, ServiceException
from api.common.utils.currency import get_points_per_npr
from api.common.utils.helpers import convert_points_to_amount
from api.user.points.models import UserPoints


class PaymentCalculationService(BaseService):
    """Service for payment calculations."""

    PAYMENT_MODE_CHOICES = {'wallet', 'points', 'wallet_points', 'direct'}
    CURRENCY_QUANTIZE = Decimal('0.01')

    def calculate_payment_options(self, user, scenario: str, **kwargs) -> Dict[str, Any]:
        """
        Calculate payment options for rental scenarios.
        
        Scenarios:
        - pre_payment: Package purchase with upfront payment
        - post_payment: Rental settlement with usage-based or overdue charges
        
        Payment modes:
        - wallet: Pay using wallet balance only
        - points: Pay using  UserPoints only
        - wallet_points: Combined wallet + UserPoints payment
        - direct: Gateway payment (no wallet/UserPoints used)
        """
        try:
            payment_mode = kwargs.get('payment_mode') or 'wallet_points'
            wallet_amount = kwargs.get('wallet_amount')
            points_to_use = kwargs.get('points_to_use')
            
            self._validate_payment_mode(payment_mode, wallet_amount, points_to_use)
            
            amount = self._get_payable_amount(user, scenario, **kwargs)
            points_per_npr = get_points_per_npr(default=10)
            user_points = self._get_user_points(user)
            wallet_balance = self._quantize(self._get_wallet_balance(user))
            points_value = self._quantize(convert_points_to_amount(user_points, points_per_unit=points_per_npr))

            # Calculate payment breakdown based on mode
            if payment_mode == 'direct':
                breakdown = self._direct_payment_breakdown(amount)
                total_available = Decimal('0.00')
            else:
                breakdown = self._calculate_payment_breakdown(
                    amount, user_points, wallet_balance, payment_mode,
                    wallet_amount, points_to_use, points_per_npr
                )
                total_available = self._get_mode_available_balance(payment_mode, wallet_balance, points_value)

            # Calculate remaining balances after payment
            remaining_points = max(0, user_points - breakdown['points_to_use'])
            remaining_wallet = self._quantize(max(Decimal('0.00'), wallet_balance - breakdown['wallet_amount']))

            return {
                'scenario': scenario,
                'payment_mode': payment_mode,
                'total_amount': amount,
                'user_balances': {
                    'points': user_points,
                    'wallet': wallet_balance,
                    'points_value': points_value,
                    'points_to_npr_rate': float(points_per_npr),
                    'total_available': self._quantize(points_value + wallet_balance),
                    'total_available_for_mode': self._quantize(total_available),
                },
                'payment_breakdown': {
                    # Backward-compatible aliases
                    'points_used': breakdown['points_to_use'],
                    'wallet_used': breakdown['wallet_amount'],
                    # Canonical keys
                    'points_to_use': breakdown['points_to_use'],
                    'points_amount': breakdown['points_amount'],
                    'wallet_amount': breakdown['wallet_amount'],
                    'direct_amount': breakdown['direct_amount'],
                    'requested_split': breakdown.get('requested_split'),
                    'remaining_balance': {
                        'points': remaining_points,
                        'wallet': remaining_wallet
                    }
                },
                'is_sufficient': breakdown['is_sufficient'],
                'shortfall': breakdown['shortfall'],
                'wallet_shortfall': breakdown['wallet_shortfall'],
                'points_shortfall': breakdown['points_shortfall'],
                'points_shortfall_amount': breakdown['points_shortfall_amount'],
                # Backward-compatible alias used by existing flows/callers
                'topup_amount_required': breakdown['shortfall'],
                'suggested_topup': self._calculate_suggested_topup(breakdown['shortfall']),
                'wallet_topup_note': 'If insufficient funds, use /api/payments/wallet/topup-intent to add money to wallet',
            }

        except Exception as e:
            self.handle_service_error(e, "Failed to calculate payment options")

    def calculate_package_payment_options(self, user, package_id: str) -> Dict[str, Any]:
        """Calculate payment options for a rental package."""
        try:
            from api.user.rentals.models import RentalPackage
            RentalPackage.objects.get(id=package_id, is_active=True)
            return self.calculate_payment_options(user=user, scenario='pre_payment', package_id=package_id)
        except Exception as e:
            self.handle_service_error(e, "Failed to calculate package payment options")

    def _get_payable_amount(self, user, scenario: str, **kwargs) -> Decimal:
        """Determine payable amount based on scenario."""
        if scenario == 'pre_payment':
            return self._get_prepayment_amount(**kwargs)
        elif scenario == 'post_payment':
            return self._get_postpayment_amount(user, **kwargs)
        else:
            raise ServiceException(
                detail="Invalid scenario. Use 'pre_payment' or 'post_payment'",
                code="invalid_scenario"
            )

    def _get_prepayment_amount(self, **kwargs) -> Decimal:
        """Get amount for pre-payment scenario."""
        package_id = kwargs.get('package_id')
        if not package_id:
            raise ServiceException(detail="package_id required for pre_payment", code="package_required")
        
        from api.user.rentals.models import RentalPackage
        package = RentalPackage.objects.get(id=package_id, is_active=True)
        
        if package.payment_model != 'PREPAID':
            raise ServiceException(
                detail=f"Package uses {package.payment_model} model, not suitable for pre-payment",
                code="invalid_package_payment_model"
            )
        
        amount = Decimal(str(kwargs['amount'])) if kwargs.get('amount') is not None else package.price
        return self._quantize(amount)

    def _get_postpayment_amount(self, user, **kwargs) -> Decimal:
        """Get amount for post-payment scenario."""
        rental_id = kwargs.get('rental_id')
        if not rental_id:
            raise ServiceException(detail="rental_id required for post_payment", code="rental_required")
        
        from api.user.rentals.models import Rental
        rental = Rental.objects.get(id=rental_id, user=user)
        
        if kwargs.get('amount') is not None:
            amount = Decimal(str(kwargs['amount']))
        elif rental.package.payment_model == 'POSTPAID':
            amount = self._calculate_postpaid_rental_amount(rental)
        else:
            amount = rental.overdue_amount or rental.package.price
        
        return self._quantize(amount)

    def _calculate_postpaid_rental_amount(self, rental) -> Decimal:
        """Calculate usage-based amount with late fees for postpaid rental."""
        if not (rental.ended_at and rental.started_at):
            return rental.package.price
        
        # Calculate base usage amount
        usage_minutes = int((rental.ended_at - rental.started_at).total_seconds() / 60)
        rate_per_minute = rental.package.price / rental.package.duration_minutes
        amount = Decimal(str(usage_minutes)) * rate_per_minute
        
        # Add late fee if overdue
        if rental.ended_at > rental.due_at:
            from api.common.utils.helpers import calculate_late_fee_amount, calculate_overdue_minutes
            overdue_minutes = calculate_overdue_minutes(rental)
            if overdue_minutes > 0:
                amount += calculate_late_fee_amount(rate_per_minute, overdue_minutes)
        
        return amount

    def _calculate_payment_breakdown(
        self, amount: Decimal, user_points: int, wallet_balance: Decimal,
        payment_mode: str, wallet_amount, points_to_use, points_per_npr: int
    ) -> Dict[str, Any]:
        """Calculate payment breakdown based on mode."""
        if payment_mode == 'wallet':
            return self._wallet_only_breakdown(amount, wallet_balance)
        elif payment_mode == 'points':
            return self._points_only_breakdown(amount, user_points, points_per_npr)
        elif payment_mode == 'wallet_points':
            return self._combined_breakdown(
                amount, user_points, wallet_balance, wallet_amount, points_to_use, points_per_npr
            )
        else:
            raise ServiceException(detail=f"Unsupported payment mode: {payment_mode}", code="invalid_payment_mode")

    def _wallet_only_breakdown(self, amount: Decimal, wallet_balance: Decimal) -> Dict[str, Any]:
        """Calculate wallet-only payment breakdown."""
        wallet_used = min(wallet_balance, amount)
        shortfall = max(Decimal('0.00'), amount - wallet_balance)
        
        return {
            'points_to_use': 0,
            'points_amount': Decimal('0.00'),
            'wallet_amount': wallet_used,
            'direct_amount': Decimal('0.00'),
            'requested_split': None,
            'is_sufficient': shortfall == Decimal('0.00'),
            'shortfall': shortfall,
            'wallet_shortfall': shortfall,
            'points_shortfall': 0,
            'points_shortfall_amount': Decimal('0.00'),
        }

    def _points_only_breakdown(self, amount: Decimal, user_points: int, points_per_npr: int) -> Dict[str, Any]:
        """Calculate points-only payment breakdown."""
        points_needed_ceil = self._amount_to_points(amount, points_per_npr, ROUND_CEILING)
        
        # User has enough points to cover amount (may need 1 extra due to rounding)
        if user_points >= points_needed_ceil:
            return {
                'points_to_use': points_needed_ceil,
                'points_amount': amount,
                'wallet_amount': Decimal('0.00'),
                'direct_amount': Decimal('0.00'),
                'requested_split': None,
                'is_sufficient': True,
                'shortfall': Decimal('0.00'),
                'wallet_shortfall': Decimal('0.00'),
                'points_shortfall': 0,
                'points_shortfall_amount': Decimal('0.00'),
            }
        
        # User doesn't have enough points - use what they have
        points_needed_floor = self._amount_to_points(amount, points_per_npr, ROUND_FLOOR)
        points_used = min(user_points, points_needed_floor)
        points_amount = self._quantize(convert_points_to_amount(points_used, points_per_unit=points_per_npr))
        shortfall = max(Decimal('0.00'), amount - points_amount)
        points_shortfall = max(0, points_needed_ceil - user_points)
        
        return {
            'points_to_use': points_used,
            'points_amount': points_amount,
            'wallet_amount': Decimal('0.00'),
            'direct_amount': Decimal('0.00'),
            'requested_split': None,
            'is_sufficient': False,
            'shortfall': shortfall,
            'wallet_shortfall': shortfall,
            'points_shortfall': points_shortfall,
            'points_shortfall_amount': self._quantize(convert_points_to_amount(points_shortfall, points_per_unit=points_per_npr)),
        }

    def _combined_breakdown(
        self, amount: Decimal, user_points: int, wallet_balance: Decimal,
        wallet_amount, points_to_use, points_per_npr: int
    ) -> Dict[str, Any]:
        """Calculate combined wallet+points payment breakdown."""
        # User specified exact split
        if wallet_amount is not None and points_to_use is not None:
            return self._user_specified_split(
                amount, user_points, wallet_balance, wallet_amount, points_to_use, points_per_npr
            )
        
        # Auto-split: maximize points usage, wallet covers remainder
        points_floor = self._amount_to_points(amount, points_per_npr, ROUND_FLOOR)
        points_ceil = self._amount_to_points(amount, points_per_npr, ROUND_CEILING)
        
        points_used = min(user_points, points_floor)
        points_amount = self._quantize(convert_points_to_amount(points_used, points_per_unit=points_per_npr))
        wallet_needed = max(Decimal('0.00'), amount - points_amount)
        
        # If wallet is short due to point rounding and user has extra point, use it to avoid wallet shortfall
        if wallet_needed > wallet_balance and user_points >= points_ceil:
            points_used = points_ceil
            points_amount = amount
            wallet_needed = Decimal('0.00')
        
        shortfall = max(Decimal('0.00'), wallet_needed - wallet_balance)
        
        return {
            'points_to_use': points_used,
            'points_amount': points_amount,
            'wallet_amount': wallet_needed,
            'direct_amount': Decimal('0.00'),
            'requested_split': None,
            'is_sufficient': shortfall == Decimal('0.00'),
            'shortfall': shortfall,
            'wallet_shortfall': shortfall,
            'points_shortfall': 0,
            'points_shortfall_amount': Decimal('0.00'),
        }

    def _user_specified_split(
        self, amount: Decimal, user_points: int, wallet_balance: Decimal,
        wallet_amount, points_to_use, points_per_npr: int
    ) -> Dict[str, Any]:
        """Calculate breakdown for user-specified wallet+points split."""
        try:
            requested_wallet = self._quantize(Decimal(str(wallet_amount)))
            requested_points = int(points_to_use)
        except (InvalidOperation, TypeError, ValueError):
            raise ServiceException(detail="Invalid wallet_amount or points_to_use", code="invalid_wallet_points_split")
        
        if requested_wallet < 0 or requested_points < 0:
            raise ServiceException(detail="wallet_amount and points_to_use must be non-negative", code="invalid_wallet_points_split")
        
        # Validate that requested split equals total amount
        requested_points_amount = self._quantize(convert_points_to_amount(requested_points, points_per_unit=points_per_npr))
        requested_total = self._quantize(requested_wallet + requested_points_amount)
        
        if requested_total != amount:
            raise ServiceException(
                detail="Split must equal total amount",
                code="split_total_mismatch",
                context={'requested_total': str(requested_total), 'expected_total': str(amount)}
            )
        
        # Calculate what user can actually pay
        wallet_used = min(wallet_balance, requested_wallet)
        points_used = min(user_points, requested_points)
        points_amount = self._quantize(convert_points_to_amount(points_used, points_per_unit=points_per_npr))
        
        wallet_shortfall = max(Decimal('0.00'), requested_wallet - wallet_balance)
        points_shortfall = max(0, requested_points - user_points)
        points_shortfall_amount = self._quantize(convert_points_to_amount(points_shortfall, points_per_unit=points_per_npr))
        
        return {
            'points_to_use': points_used,
            'points_amount': points_amount,
            'wallet_amount': wallet_used,
            'direct_amount': Decimal('0.00'),
            'requested_split': {
                'wallet_amount': requested_wallet,
                'points_to_use': requested_points,
                'points_amount': requested_points_amount
            },
            'is_sufficient': wallet_shortfall == 0 and points_shortfall == 0,
            'shortfall': self._quantize(wallet_shortfall + points_shortfall_amount),
            'wallet_shortfall': wallet_shortfall,
            'points_shortfall': points_shortfall,
            'points_shortfall_amount': points_shortfall_amount,
        }

    def _direct_payment_breakdown(self, amount: Decimal) -> Dict[str, Any]:
        """Return breakdown for direct gateway payment (no wallet/points used)."""
        return {
            'points_to_use': 0,
            'points_amount': Decimal('0.00'),
            'wallet_amount': Decimal('0.00'),
            'direct_amount': amount,
            'requested_split': None,
            'is_sufficient': False,
            'shortfall': amount,
            'wallet_shortfall': amount,
            'points_shortfall': 0,
            'points_shortfall_amount': Decimal('0.00'),
        }

    def _validate_payment_mode(self, payment_mode: str, wallet_amount, points_to_use) -> None:
        """Validate payment mode and split parameters."""
        if payment_mode not in self.PAYMENT_MODE_CHOICES:
            raise ServiceException(
                detail=f"Invalid payment mode. Use: {', '.join(sorted(self.PAYMENT_MODE_CHOICES))}",
                code="invalid_payment_mode"
            )
        
        has_wallet = wallet_amount is not None
        has_points = points_to_use is not None
        
        # Both or neither must be provided together
        if has_wallet ^ has_points:
            raise ServiceException(
                detail="Provide both wallet_amount and points_to_use together or neither",
                code="invalid_wallet_points_split"
            )
        
        # Split params only valid for wallet_points mode
        if payment_mode != 'wallet_points' and (has_wallet or has_points):
            raise ServiceException(
                detail="wallet_amount and points_to_use only valid for wallet_points mode",
                code="invalid_wallet_points_split"
            )

    def _get_mode_available_balance(self, payment_mode: str, wallet_balance: Decimal, points_value: Decimal) -> Decimal:
        """Get available balance for the selected payment mode."""
        if payment_mode == 'wallet':
            return wallet_balance
        elif payment_mode == 'points':
            return points_value
        else:  # wallet_points
            return wallet_balance + points_value

    def _calculate_suggested_topup(self, shortfall: Decimal) -> int:
        """Calculate suggested top-up amount (rounded to next 100)."""
        return ((shortfall // 100) + 1) * 100 if shortfall > 0 else None

    def _quantize(self, amount: Decimal) -> Decimal:
        """Normalize decimal to 2-decimal currency precision."""
        return Decimal(str(amount)).quantize(self.CURRENCY_QUANTIZE)

    def _amount_to_points(self, amount: Decimal, points_per_npr: int, rounding) -> int:
        """Convert currency amount to points with specified rounding."""
        normalized = self._quantize(amount)
        return int((normalized * Decimal(str(points_per_npr))).to_integral_value(rounding=rounding))

    def _get_user_points(self, user) -> int:
        """Get user's current loyalty points balance."""
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
