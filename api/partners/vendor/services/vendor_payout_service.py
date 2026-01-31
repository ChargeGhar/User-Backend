"""
Vendor Payout Service

Handles vendor payout operations.
"""

from decimal import Decimal
from rest_framework.exceptions import PermissionDenied

from api.common.utils.helpers import paginate_queryset
from api.partners.common.repositories import (
    PartnerRepository,
    PayoutRequestRepository
)
from api.partners.common.models import PayoutRequest


class VendorPayoutService:
    """Service for vendor payout operations"""
    
    @staticmethod
    def get_payout_list(vendor_id: str, filters: dict) -> dict:
        """
        Get vendor's payout history.
        
        BR12.7: Only own payouts
        """
        # Get payouts
        queryset = PayoutRequestRepository.get_by_partner(
            partner_id=vendor_id,
            status=filters.get('status'),
            start_date=filters.get('start_date'),
            end_date=filters.get('end_date')
        )
        
        # Get summary
        summary = PayoutRequestRepository.get_summary_by_partner(vendor_id)
        
        # Paginate
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        paginated_data = paginate_queryset(queryset, page, page_size)
        
        # Build results
        results = []
        for payout in paginated_data['results']:
            results.append({
                'id': str(payout.id),
                'reference_id': payout.reference_id,
                'amount': payout.amount,
                'net_amount': payout.net_amount,
                'status': payout.status,
                'payout_type': payout.payout_type,
                'bank_name': payout.bank_name,
                'account_number': payout.account_number,
                'account_holder_name': payout.account_holder_name,
                'requested_at': payout.created_at,
                'processed_at': payout.processed_at,
                'processed_by': {
                    'id': payout.processed_by.id,
                    'username': payout.processed_by.username,
                    'email': payout.processed_by.email
                } if payout.processed_by else None,
                'rejection_reason': payout.rejection_reason,
                'admin_notes': payout.admin_notes
            })
        
        return {
            'results': results,
            'pagination': paginated_data['pagination'],
            'summary': {
                'pending_amount': summary.get('pending_amount', Decimal('0')),
                'total_paid': summary.get('total_paid', Decimal('0'))
            }
        }
    
    @staticmethod
    def request_payout(vendor_id: str, data: dict) -> dict:
        """
        Request new payout.
        
        BR8.4: Revenue vendors only
        BR12.7: Own balance only
        """
        # Get vendor
        vendor = PartnerRepository.get_by_id(vendor_id)
        if not vendor:
            raise ValueError("Vendor not found")
        
        # Validate: Revenue vendor only (BR8.4)
        if not vendor.is_revenue_vendor:
            raise PermissionDenied("Non-revenue vendors cannot request payouts")
        
        # Validate: Amount
        amount = Decimal(str(data['amount']))
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        if amount > vendor.balance:
            raise ValueError(f"Insufficient balance. Available: {vendor.balance}")
        
        # Validate: No pending payout
        pending = PayoutRequestRepository.get_by_partner(
            partner_id=vendor_id,
            status=PayoutRequest.Status.PENDING
        ).exists()
        if pending:
            raise ValueError("You already have a pending payout request")
        
        # Validate: Bank details
        if not data.get('bank_name') or not data.get('account_number') or not data.get('account_holder_name'):
            raise ValueError("Bank details are required")
        
        # Create payout request
        payout = PayoutRequestRepository.create(
            partner_id=vendor_id,
            amount=amount,
            bank_name=data['bank_name'],
            account_number=data['account_number'],
            account_holder_name=data['account_holder_name']
        )
        
        return {
            'id': str(payout.id),
            'reference_id': payout.reference_id,
            'amount': payout.amount,
            'net_amount': payout.net_amount,
            'status': payout.status,
            'payout_type': payout.payout_type,
            'bank_name': payout.bank_name,
            'account_number': payout.account_number,
            'account_holder_name': payout.account_holder_name,
            'requested_at': payout.created_at,
            'processor': payout.processor_entity()
        }
