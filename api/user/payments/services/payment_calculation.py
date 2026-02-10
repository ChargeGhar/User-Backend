from __future__ import annotations

from typing import Dict, Any
from decimal import Decimal

from api.common.services.base import BaseService, ServiceException
from api.common.utils.helpers import convert_points_to_amount
from api.user.points.models import UserPoints

class PaymentCalculationService(BaseService):
    """Service for payment calculations"""

    def calculate_payment_options(self, user, scenario: str, **kwargs) -> Dict[str, Any]:
        """
        Calculate payment options for rental scenarios.
        
        Scenarios:
        - pre_payment: Calculate package cost using package.payment_model (PREPAID only)
        - post_payment: Calculate rental dues including overdue charges
        
        Points are ALWAYS used first, then wallet balance.
        """
        try:
            # Extract parameters
            package_id = kwargs.get('package_id')
            rental_id = kwargs.get('rental_id')

            # Determine amount based on scenario
            if scenario == 'pre_payment':
                if not package_id:
                    raise ServiceException(
                        detail="Package ID required for pre-payment calculation",
                        code="package_required"
                    )
                # Get amount from package price
                from api.user.rentals.models import RentalPackage
                package = RentalPackage.objects.get(id=package_id, is_active=True)
                amount_override = kwargs.get('amount')
                amount = Decimal(str(amount_override)) if amount_override is not None else package.price
                
                # Validate this is a prepaid package
                if package.payment_model != 'PREPAID':
                    raise ServiceException(
                        detail=f"Package '{package.name}' uses {package.payment_model} model, not suitable for pre-payment calculation",
                        code="invalid_package_payment_model"
                    )
                    
            elif scenario == 'post_payment':
                if not rental_id:
                    raise ServiceException(
                        detail="Rental ID required for post-payment calculation",
                        code="rental_required"
                    )
                # Calculate amount based on rental dues
                from api.user.rentals.models import Rental
                rental = Rental.objects.get(id=rental_id, user=user)
                # Calculate dues including overdue amounts
                if rental.package.payment_model == 'POSTPAID':
                    # Calculate actual usage cost
                    if rental.ended_at and rental.started_at:
                        usage_duration = rental.ended_at - rental.started_at
                        usage_minutes = int(usage_duration.total_seconds() / 60)
                        package_rate_per_minute = rental.package.price / rental.package.duration_minutes
                        amount = Decimal(str(usage_minutes)) * package_rate_per_minute

                        # Add overdue charges if applicable
                        if rental.ended_at > rental.due_at:
                            from api.common.utils.helpers import calculate_overdue_minutes, calculate_late_fee_amount
                            overdue_minutes = calculate_overdue_minutes(rental)
                            if overdue_minutes > 0:
                                late_fee = calculate_late_fee_amount(package_rate_per_minute, overdue_minutes)
                                amount += late_fee

                                # Send fines/dues notification
                                from api.user.notifications.services import notify
                                notify(
                                    user,
                                    'fines_dues',
                                    async_send=True,
                                    amount=float(late_fee),
                                    reason=f"Late return penalty - {overdue_minutes} minutes overdue"
                                )
                        else:
                            # Use package price as fallback
                            amount = rental.package.price
                    else:
                        # Use package price if duration not available
                        amount = rental.package.price
                else:
                    # Use overdue amount for prepaid models with dues
                    amount = rental.overdue_amount or rental.package.price
            else:
                raise ServiceException(
                    detail="Invalid scenario. Supported scenarios: pre_payment, post_payment",
                    code="invalid_scenario"
                )

            # Get user's current points and wallet balance
            user_points = self._get_user_points(user)
            wallet_balance = self._get_wallet_balance(user)

            # Convert points to monetary value (10 points = NPR 1)
            points_value = convert_points_to_amount(user_points)

            # Calculate payment breakdown
            payment_breakdown = self._calculate_payment_breakdown(
                amount, user_points, wallet_balance, points_value
            )

            # Check if user has sufficient funds
            total_available = points_value + wallet_balance
            is_sufficient = total_available >= amount
            shortfall = max(Decimal('0'), amount - total_available)

            # Suggest top-up amount if needed
            suggested_topup = None
            if not is_sufficient:
                # Round up to nearest 100 for convenience
                suggested_topup = ((shortfall // 100) + 1) * 100

            return {
                'scenario': scenario,
                'total_amount': amount,
                'user_balances': {
                    'points': user_points,
                    'wallet': wallet_balance,
                    'points_to_npr_rate': 10.0  # 10 points = NPR 1
                },
                'payment_breakdown': {
                    'points_used': payment_breakdown['points_to_use'],
                    'points_amount': payment_breakdown['points_amount'],
                    'wallet_used': payment_breakdown['wallet_amount'],
                    'remaining_balance': {
                        'points': user_points - payment_breakdown['points_to_use'],
                        'wallet': wallet_balance - payment_breakdown['wallet_amount']
                    }
                },
                'is_sufficient': is_sufficient,
                'shortfall': shortfall,
                'suggested_topup': suggested_topup,
                'wallet_topup_note': 'If insufficient funds, use /api/payments/wallet/topup-intent to add money to wallet'
            }

        except Exception as e:
            self.handle_service_error(e, "Failed to calculate payment options")

    def calculate_package_payment_options(self, user, package_id: str) -> Dict[str, Any]:
        """
        Calculate payment options for a specific rental package.
        Automatically determines scenario based on package.payment_model.
        
        This is the preferred method for rental-related calculations.
        """
        try:
            from api.user.rentals.models import RentalPackage
            package = RentalPackage.objects.get(id=package_id, is_active=True)
            
            # Determine scenario based on package payment model
            if package.payment_model == 'PREPAID':
                scenario = 'pre_payment'
            else:
                # For POSTPAID, we still show what would be charged (for preview)
                scenario = 'pre_payment'  # Use same calculation logic
                
            return self.calculate_payment_options(
                user=user,
                scenario=scenario,
                package_id=package_id
            )
            
        except Exception as e:
            self.handle_service_error(e, "Failed to calculate package payment options")

    def _get_user_points(self, user) -> int:
        """Get user's current points"""
        try:
            return user.points.current_points
        except UserPoints.DoesNotExist:
            return 0

    def _get_wallet_balance(self, user) -> Decimal:
        """Get user's wallet balance"""
        try:
            return user.wallet.balance
        except:
            return Decimal('0')

    def _calculate_payment_breakdown(self, amount: Decimal, user_points: int, wallet_balance: Decimal, points_value: Decimal) -> Dict[str, Any]:
        """Calculate how payment will be split between points and wallet"""
        # Use points first, then wallet
        points_to_use = 0
        points_amount = Decimal('0')
        wallet_amount = Decimal('0')

        if points_value >= amount:
            # Points are sufficient
            points_amount = amount
            points_to_use = int(amount * 10)  # Convert back to points (NPR 1 = 10 points)
        else:
            # Use all points, then wallet
            points_amount = points_value
            points_to_use = user_points
            wallet_amount = amount - points_value

        return {
            'points_to_use': points_to_use,
            'points_amount': points_amount,
            'wallet_amount': wallet_amount,
            'total_amount': points_amount + wallet_amount
        }
