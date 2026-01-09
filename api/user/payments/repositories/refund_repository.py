from typing import Optional, Dict, Any
from django.db.models import QuerySet
from api.user.payments.models import Refund

class RefundRepository:
    """Repository for Refund data operations"""
    
    @staticmethod
    def get_by_id(refund_id: str) -> Optional[Refund]:
        try:
            return Refund.objects.get(id=refund_id)
        except Refund.DoesNotExist:
            return None

    @staticmethod
    def get_by_refund_id(refund_id_str: str) -> Optional[Refund]:
        try:
            return Refund.objects.get(refund_id=refund_id_str)
        except Refund.DoesNotExist:
            return None

    @staticmethod
    def get_by_user(user) -> QuerySet:
        return Refund.objects.filter(requested_by=user).select_related('transaction')

    @staticmethod
    def get_queryset() -> QuerySet:
        return Refund.objects.all().order_by('-created_at')

    @staticmethod
    def get_requests(filters: Dict[str, Any] = None) -> QuerySet:
        queryset = Refund.objects.all().order_by('-created_at')
        if filters:
            if 'status' in filters and filters['status']:
                queryset = queryset.filter(status=filters['status'])
            if 'user_id' in filters and filters['user_id']:
                queryset = queryset.filter(requested_by_id=filters['user_id'])
            if 'start_date' in filters and filters['start_date']:
                queryset = queryset.filter(created_at__date__gte=filters['start_date'])
            if 'end_date' in filters and filters['end_date']:
                queryset = queryset.filter(created_at__date__lte=filters['end_date'])
        return queryset

    @staticmethod
    def get_pending_requests(filters: Dict[str, Any] = None) -> QuerySet:
        if filters is None:
            filters = {}
        filters['status'] = 'REQUESTED'
        return RefundRepository.get_requests(filters)

    @staticmethod
    def create(
        user,
        transaction,
        amount,
        reason: str,
        refund_id: str,
        status: str = 'REQUESTED'
    ) -> Refund:
        return Refund.objects.create(
            requested_by=user,
            transaction=transaction,
            amount=amount,
            reason=reason,
            refund_id=refund_id,
            status=status
        )
