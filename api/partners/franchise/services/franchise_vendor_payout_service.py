"""
Franchise Vendor Payout Service

Service layer for franchise vendor payout management operations.
"""

from django.db import transaction

from api.common.services.base import BaseService, ServiceException
from api.common.utils.pagination import paginate_queryset
from api.partners.common.models import Partner, PayoutRequest
from api.partners.common.repositories import PayoutRequestRepository


class FranchiseVendorPayoutService(BaseService):
    """Service for franchise vendor payout management"""
    
    def get_vendor_payouts_list(self, franchise: Partner, filters: dict) -> dict:
        """
        Get vendor payout requests (franchise pays vendors).
        
        BR8.3: Franchise pays Franchise-level Vendors
        BR10.2: Only own vendors
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        queryset = PayoutRequest.objects.filter(
            payout_type=PayoutRequest.PayoutType.FRANCHISE_TO_VENDOR
        ).select_related('partner').filter(
            partner__parent_id=franchise.id
        ).order_by('-created_at')
        
        # Apply filters
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('vendor_id'):
            queryset = queryset.filter(partner_id=filters['vendor_id'])
        
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
                'vendor': {
                    'id': payout.partner.id,
                    'code': payout.partner.code,
                    'business_name': payout.partner.business_name,
                },
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
    
    def approve_vendor_payout(self, franchise: Partner, payout_id: str) -> PayoutRequest:
        """
        Approve vendor payout request.
        
        BR10.2: Only own vendors
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        payout = PayoutRequest.objects.select_related('partner').filter(
            id=payout_id,
            payout_type=PayoutRequest.PayoutType.FRANCHISE_TO_VENDOR,
            partner__parent_id=franchise.id
        ).first()
        
        if not payout:
            raise ServiceException(
                detail="Payout request not found",
                code="PAYOUT_NOT_FOUND"
            )
        
        if payout.status != PayoutRequest.Status.PENDING:
            raise ServiceException(
                detail=f"Cannot approve payout with status: {payout.status}",
                code="INVALID_STATUS"
            )
        
        payout = PayoutRequestRepository.update_status(
            payout_id=str(payout.id),
            status=PayoutRequest.Status.APPROVED
        )
        
        self.log_info(f"Vendor payout approved: {payout.reference_id} by franchise {franchise.id}")
        return payout
    
    def reject_vendor_payout(self, franchise: Partner, payout_id: str, reason: str) -> PayoutRequest:
        """
        Reject vendor payout request.
        
        BR10.2: Only own vendors
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        payout = PayoutRequest.objects.select_related('partner').filter(
            id=payout_id,
            payout_type=PayoutRequest.PayoutType.FRANCHISE_TO_VENDOR,
            partner__parent_id=franchise.id
        ).first()
        
        if not payout:
            raise ServiceException(
                detail="Payout request not found",
                code="PAYOUT_NOT_FOUND"
            )
        
        if payout.status != PayoutRequest.Status.PENDING:
            raise ServiceException(
                detail=f"Cannot reject payout with status: {payout.status}",
                code="INVALID_STATUS"
            )
        
        payout = PayoutRequestRepository.update_status(
            payout_id=str(payout.id),
            status=PayoutRequest.Status.REJECTED,
            rejection_reason=reason
        )
        
        self.log_info(f"Vendor payout rejected: {payout.reference_id} by franchise {franchise.id}")
        return payout
    
    def complete_vendor_payout(self, franchise: Partner, payout_id: str) -> PayoutRequest:
        """
        Complete vendor payout - deduct from both balances.
        
        BR8.3: Franchise pays Franchise-level Vendors
        BR8.5: Franchise receives payout BEFORE paying vendors
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        payout = PayoutRequest.objects.select_related('partner').filter(
            id=payout_id,
            payout_type=PayoutRequest.PayoutType.FRANCHISE_TO_VENDOR,
            partner__parent_id=franchise.id
        ).first()
        
        if not payout:
            raise ServiceException(
                detail="Payout request not found",
                code="PAYOUT_NOT_FOUND"
            )
        
        if payout.status != PayoutRequest.Status.APPROVED:
            raise ServiceException(
                detail=f"Cannot complete payout with status: {payout.status}. Must be APPROVED.",
                code="INVALID_STATUS"
            )
        
        vendor = payout.partner
        
        # Validate balances
        if payout.amount > vendor.balance:
            raise ServiceException(
                detail=f"Insufficient vendor balance. Available: {vendor.balance}",
                code="INSUFFICIENT_VENDOR_BALANCE"
            )
        
        if payout.amount > franchise.balance:
            raise ServiceException(
                detail=f"Insufficient franchise balance. Available: {franchise.balance}",
                code="INSUFFICIENT_FRANCHISE_BALANCE"
            )
        
        # Atomic balance deduction
        with transaction.atomic():
            # Deduct from vendor
            vendor.balance -= payout.amount
            vendor.save(update_fields=['balance'])
            
            # Deduct from franchise
            franchise.balance -= payout.amount
            franchise.save(update_fields=['balance'])
            
            # Update payout status
            payout = PayoutRequestRepository.update_status(
                payout_id=str(payout.id),
                status=PayoutRequest.Status.COMPLETED
            )
        
        self.log_info(f"Vendor payout completed: {payout.reference_id} by franchise {franchise.id}")
        return payout
