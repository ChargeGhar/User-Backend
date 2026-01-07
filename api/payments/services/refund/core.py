from __future__ import annotations

from typing import Dict, Any, Optional
from decimal import Decimal

from api.common.services.base import CRUDService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.payments.models import Refund
from api.payments.repositories import RefundRepository, TransactionRepository

class RefundBaseService(CRUDService):
    """Base service for refund operations"""
    model = Refund

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.refund_repository = RefundRepository()
        self.transaction_repository = TransactionRepository()

    def get_user_refunds(self, user, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get user's refund requests"""
        try:
            queryset = self.refund_repository.get_by_user(user)
            return paginate_queryset(queryset, page, page_size)
        except Exception as e:
            self.handle_service_error(e, "Failed to get user refunds")

    def get_refund_by_id(self, refund_id: str) -> Refund:
        """Get refund by ID with related data"""
        try:
            refund = self.refund_repository.get_by_id(refund_id)
            if not refund:
                raise ServiceException(
                    detail=f"Refund with ID {refund_id} not found",
                    code="refund_not_found"
                )
            return refund
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to get refund details")

    def get_pending_refunds(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get pending refund requests (Admin)"""
        try:
            page = int(filters.get('page', 1)) if filters else 1
            page_size = int(filters.get('page_size', 20)) if filters else 20
            queryset = self.refund_repository.get_pending_requests(filters).select_related('requested_by', 'transaction')
            return paginate_queryset(queryset, page, page_size)
        except Exception as e:
            self.handle_service_error(e, "Failed to get pending refunds")

    def get_refunds_by_status(self, status: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get refunds by status (Admin)"""
        try:
            filters = {'status': status}
            queryset = self.refund_repository.get_requests(filters).select_related('requested_by', 'transaction')
            return paginate_queryset(queryset, page, page_size)
        except Exception as e:
            self.handle_service_error(e, f"Failed to get refunds with status {status}")
