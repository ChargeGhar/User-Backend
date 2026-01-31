"""
Franchise Payout Service

Service layer for franchise own payout operations.
"""

from decimal import Decimal

from api.common.services.base import BaseService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.partners.common.models import Partner, PayoutRequest
from api.partners.common.repositories import PayoutRequestRepository


class FranchisePayoutService(BaseService):
    """Service for franchise own payout operations"""
    
    def request_payout(
        self,
        franchise: Partner,
        amount: Decimal,
        bank_name: str,
        account_number: str,
        account_holder_name: str
    ) -> PayoutRequest:
        """
        Request payout from ChargeGhar.
        
        BR8.1: ChargeGhar pays Franchises
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        # Validate amount
        if amount <= 0:
            raise ServiceException(
                detail="Amount must be greater than 0",
                code="INVALID_AMOUNT"
            )
        
        if amount > franchise.balance:
            raise ServiceException(
                detail=f"Insufficient balance. Available: {franchise.balance}",
                code="INSUFFICIENT_BALANCE"
            )
        
        # Check for pending payout
        pending = PayoutRequest.objects.filter(
            partner_id=franchise.id,
            payout_type=PayoutRequest.PayoutType.CHARGEGHAR_TO_FRANCHISE,
            status=PayoutRequest.Status.PENDING
        ).exists()
        
        if pending:
            raise ServiceException(
                detail="You already have a pending payout request",
                code="PENDING_PAYOUT_EXISTS"
            )
        
        # Create payout request
        payout = PayoutRequestRepository.create(
            partner_id=str(franchise.id),
            amount=amount,
            bank_name=bank_name,
            account_number=account_number,
            account_holder_name=account_holder_name
        )
        
        self.log_info(f"Payout requested: {payout.reference_id} by franchise {franchise.id}")
        return payout
    
    def get_payouts_list(self, franchise: Partner, filters: dict) -> dict:
        """
        Get franchise's own payout requests (from ChargeGhar).
        
        BR8.1: ChargeGhar pays Franchises
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        queryset = PayoutRequest.objects.filter(
            partner_id=franchise.id,
            payout_type=PayoutRequest.PayoutType.CHARGEGHAR_TO_FRANCHISE
        ).order_by('-created_at')
        
        # Apply filters
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        # Paginate
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        paginated = paginate_queryset(queryset, page, page_size)
        
        # Build results
        results = []
        for payout in paginated['results']:
            results.append({
                'id': payout.id,
                'reference_id': payout.reference_id,
                'amount': payout.amount,
                'net_amount': payout.net_amount,
                'status': payout.status,
                'bank_name': payout.bank_name,
                'account_number': payout.account_number,
                'account_holder_name': payout.account_holder_name,
                'rejection_reason': payout.rejection_reason,
                'created_at': payout.created_at,
                'processed_at': payout.processed_at,
            })
        
        return {
            'results': results,
            'pagination': paginated['pagination']
        }
