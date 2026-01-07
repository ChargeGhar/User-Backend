from typing import Optional, List, Dict, Any
from django.db.models import QuerySet
from api.payments.models import WithdrawalRequest, WithdrawalLimit

class WithdrawalRepository:
    """Repository for Withdrawal data operations"""
    
    @staticmethod
    def get_request_by_id(request_id: str) -> Optional[WithdrawalRequest]:
        try:
            return WithdrawalRequest.objects.get(id=request_id)
        except WithdrawalRequest.DoesNotExist:
            return None

    @staticmethod
    def get_user_requests(user) -> QuerySet:
        return WithdrawalRequest.objects.filter(user=user).order_by('-created_at')

    @staticmethod
    def get_queryset() -> QuerySet:
        return WithdrawalRequest.objects.all().order_by('-requested_at')

    @staticmethod
    def get_requests(filters: Dict[str, Any] = None) -> QuerySet:
        queryset = WithdrawalRequest.objects.all().order_by('-requested_at')
        if filters:
            if 'status' in filters and filters['status']:
                queryset = queryset.filter(status=filters['status'])
            if 'user_id' in filters and filters['user_id']:
                queryset = queryset.filter(user_id=filters['user_id'])
            if 'start_date' in filters and filters['start_date']:
                queryset = queryset.filter(requested_at__date__gte=filters['start_date'])
            if 'end_date' in filters and filters['end_date']:
                queryset = queryset.filter(requested_at__date__lte=filters['end_date'])
        return queryset

    @staticmethod
    def get_pending_requests(filters: Dict[str, Any] = None) -> QuerySet:
        if filters is None:
            filters = {}
        # Support both legacy PENDING and current REQUESTED statuses
        queryset = WithdrawalRepository.get_requests(filters)
        return queryset.filter(status__in=['REQUESTED', 'PENDING'])

    @staticmethod
    def create_request(
        user,
        amount: float,
        bank_name: str,
        account_number: str,
        account_holder_name: str,
        status: str = 'REQUESTED',
        **kwargs
    ) -> WithdrawalRequest:
        return WithdrawalRequest.objects.create(
            user=user,
            amount=amount,
            bank_name=bank_name,
            account_number=account_number,
            account_holder_name=account_holder_name,
            status=status,
            **kwargs
        )

    @staticmethod
    def get_active_limit(user_role: str = 'USER') -> Optional[WithdrawalLimit]:
        # NOTE: The current WithdrawalLimit model is per-user, not per-role.
        # This method seems to have been intended for system-wide limits which might be missing.
        # For now, we return None to let the service use config-based defaults.
        return None

    @staticmethod
    def get_or_create_user_limit(user) -> WithdrawalLimit:
        from datetime import date
        limit, _ = WithdrawalLimit.objects.get_or_create(
            user=user,
            defaults={
                'daily_withdrawn': 0, 
                'monthly_withdrawn': 0, 
                'last_daily_reset': date.today(), 
                'last_monthly_reset': date.today()
            }
        )
        return limit
