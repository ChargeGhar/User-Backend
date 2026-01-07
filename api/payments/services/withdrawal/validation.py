from __future__ import annotations

from typing import Dict, Any
from decimal import Decimal
from datetime import date

from api.common.services.base import ServiceException
from api.payments.models import WithdrawalLimit
from .core import WithdrawalBaseService

class WithdrawalValidationService(WithdrawalBaseService):
    """Service for withdrawal validation logic"""

    def validate_request(self, user, amount: Decimal, withdrawal_method: str, account_details: Dict[str, Any]) -> None:
        """Perform all validations for a withdrawal request"""
        if not amount or amount <= 0:
            raise ServiceException(detail="Amount must be greater than 0", code="invalid_amount")

        if not account_details:
            raise ServiceException(detail="Account details are required", code="account_details_required")

        # Check if enabled
        if self.config_service.get_config_cached('WITHDRAWAL_ENABLED', 'true').lower() != 'true':
            raise ServiceException(detail="Withdrawal functionality is disabled", code="withdrawals_disabled")

        # Validate method
        if not self.method_repository.get_by_gateway(withdrawal_method):
            raise ServiceException(detail=f"Method '{withdrawal_method}' is unavailable", code="invalid_method")

        # Min amount
        min_amt = Decimal(self.config_service.get_config_cached('WITHDRAWAL_MIN_AMOUNT', '100'))
        if amount < min_amt:
            raise ServiceException(detail=f"Minimum withdrawal is NPR {min_amt}", code="amount_too_low")

        # Limits
        self.validate_limits(user, amount)

        # Balance
        balance_info = self.wallet_service.get_wallet_balance(user)
        balance = balance_info.get('balance', 0) if isinstance(balance_info, dict) else balance_info
        if balance < amount:
            raise ServiceException(detail=f"Insufficient balance. Available: NPR {balance}", code="insufficient_balance")

        # Account details
        self._validate_account_details(withdrawal_method, account_details)

    def validate_limits(self, user, amount: Decimal) -> None:
        """Validate daily and monthly limits"""
        daily_limit = Decimal(self.config_service.get_config_cached('WITHDRAWAL_MAX_DAILY_LIMIT', '10000'))
        monthly_limit = Decimal(self.config_service.get_config_cached('WITHDRAWAL_MAX_MONTHLY_LIMIT', '50000'))

        # Get or create per-user withdrawal limit tracking
        withdrawal_limit = self.withdrawal_repository.get_or_create_user_limit(user)

        # Reset if needed
        today = date.today()
        if withdrawal_limit.last_daily_reset < today:
            withdrawal_limit.daily_withdrawn = 0
            withdrawal_limit.last_daily_reset = today
        
        if withdrawal_limit.last_monthly_reset < today.replace(day=1):
            withdrawal_limit.monthly_withdrawn = 0
            withdrawal_limit.last_monthly_reset = today
        
        withdrawal_limit.save()

        if withdrawal_limit.daily_withdrawn + amount > daily_limit:
            raise ServiceException(detail="Daily limit exceeded", code="daily_limit_exceeded")
        
        if withdrawal_limit.monthly_withdrawn + amount > monthly_limit:
            raise ServiceException(detail="Monthly limit exceeded", code="monthly_limit_exceeded")

    def _validate_account_details(self, method: str, details: Dict[str, Any]) -> None:
        """Validate format of account details"""
        method = method.lower()
        if method == 'bank':
            for f in ['bank_name', 'account_number', 'account_holder_name']:
                if not details.get(f):
                    raise ServiceException(detail=f"Bank {f} is required", code="missing_field")
        elif method in ['esewa', 'khalti']:
            phone = details.get('phone_number', '')
            if not phone.startswith('98') or len(phone) != 10:
                raise ServiceException(detail="Invalid phone number", code="invalid_phone")
        else:
            raise ServiceException(detail=f"Unsupported method: {method}", code="unsupported_method")
