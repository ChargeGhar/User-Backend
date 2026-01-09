from __future__ import annotations

from typing import Dict, Any

from api.common.services.base import CRUDService
from api.common.utils.helpers import paginate_queryset
from api.user.payments.models import Transaction
from api.user.payments.repositories import TransactionRepository

class TransactionService(CRUDService):
    """Service for transaction operations"""
    model = Transaction

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = TransactionRepository()

    def get_user_transactions(self, user, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get user's transaction history with filters"""
        try:
            queryset = self.get_user_transactions_queryset(user)

            # Apply filters
            if filters:
                if filters.get('transaction_type'):
                    queryset = queryset.filter(transaction_type=filters['transaction_type'])

                if filters.get('status'):
                    queryset = queryset.filter(status=filters['status'])

                if filters.get('start_date'):
                    queryset = queryset.filter(created_at__gte=filters['start_date'])

                if filters.get('end_date'):
                    queryset = queryset.filter(created_at__lte=filters['end_date'])

            # Pagination
            page = filters.get('page', 1) if filters else 1
            page_size = filters.get('page_size', 20) if filters else 20

            return paginate_queryset(queryset, page, page_size)

        except Exception as e:
            self.handle_service_error(e, "Failed to get user transactions")
    
    def get_user_transactions_queryset(self, user):
        """Get base queryset for user transactions"""
        return self.repository.get_user_transactions(user).select_related('related_rental')
