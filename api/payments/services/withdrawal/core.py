from __future__ import annotations

from typing import Dict, Any, Optional
from decimal import Decimal
from django.db import transaction

from api.common.services.base import CRUDService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.payments.models import WithdrawalRequest
from api.payments.services.wallet import WalletService
from api.payments.repositories import WithdrawalRepository, PaymentMethodRepository

class WithdrawalBaseService(CRUDService):
    """Base service for withdrawal operations"""
    model = WithdrawalRequest

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from api.system.services import AppConfigService
        self.config_service = AppConfigService()
        self.wallet_service = WalletService()
        self.withdrawal_repository = WithdrawalRepository()
        self.method_repository = PaymentMethodRepository()

    def get_user_withdrawals(self, user, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get user withdrawal history with pagination"""
        try:
            queryset = self.withdrawal_repository.get_user_requests(user).select_related('payment_method')
            return paginate_queryset(queryset, page, page_size)
        except Exception as e:
            self.handle_service_error(e, "Failed to get user withdrawals")

    def calculate_withdrawal_fee(self, amount: Decimal) -> Decimal:
        """Calculate withdrawal processing fee"""
        try:
            fee_percentage = Decimal(self.config_service.get_config_cached('WITHDRAWAL_PROCESSING_FEE_PERCENTAGE', '2.0'))
            fee_fixed = Decimal(self.config_service.get_config_cached('WITHDRAWAL_PROCESSING_FEE_FIXED', '10'))
            
            percentage_fee = (amount * fee_percentage) / 100
            total_fee = percentage_fee + fee_fixed
            
            return total_fee
        except Exception as e:
            self.log_error(f"Error calculating withdrawal fee: {str(e)}")
            return Decimal('10')  # Default fee

    def get_withdrawal_by_id(self, withdrawal_id: str) -> WithdrawalRequest:
        """Get withdrawal by ID with related data"""
        try:
            withdrawal = self.withdrawal_repository.get_request_by_id(withdrawal_id)
            if not withdrawal:
                raise ServiceException(
                    detail=f"Withdrawal with ID {withdrawal_id} not found",
                    code="withdrawal_not_found"
                )
            return withdrawal
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to get withdrawal details")

    def get_withdrawals(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get all withdrawals with filters (Admin)"""
        try:
            page = int(filters.get('page', 1)) if filters else 1
            page_size = int(filters.get('page_size', 20)) if filters else 20
            queryset = self.withdrawal_repository.get_requests(filters).select_related('payment_method', 'user')
            return paginate_queryset(queryset, page, page_size)
        except Exception as e:
            self.handle_service_error(e, "Failed to get withdrawals")

    def get_pending_withdrawals(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get pending withdrawals with filters (Admin)"""
        try:
            page = int(filters.get('page', 1)) if filters else 1
            page_size = int(filters.get('page_size', 20)) if filters else 20
            queryset = self.withdrawal_repository.get_pending_requests(filters).select_related('payment_method', 'user')
            return paginate_queryset(queryset, page, page_size)
        except Exception as e:
            self.handle_service_error(e, "Failed to get pending withdrawals")

    def get_withdrawals_by_status(self, status: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get withdrawals by status (Admin)"""
        try:
            filters = {'status': status}
            queryset = self.withdrawal_repository.get_requests(filters).select_related('payment_method', 'user')
            return paginate_queryset(queryset, page, page_size)
        except Exception as e:
            self.handle_service_error(e, f"Failed to get withdrawals with status {status}")
