from typing import Optional
from decimal import Decimal
from datetime import date
from django.db.models import QuerySet, Sum, Count
from django.utils import timezone
import uuid

from api.partners.common.models import PayoutRequest


class PayoutRequestRepository:
    """
    Repository for PayoutRequest model database operations.
    """
    
    @staticmethod
    def get_by_id(payout_id: str) -> Optional[PayoutRequest]:
        """Get payout request by ID"""
        try:
            return PayoutRequest.objects.select_related(
                'partner', 'partner__parent', 'processed_by'
            ).get(id=payout_id)
        except PayoutRequest.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_reference_id(reference_id: str) -> Optional[PayoutRequest]:
        """Get payout request by reference ID"""
        try:
            return PayoutRequest.objects.select_related(
                'partner', 'partner__parent', 'processed_by'
            ).get(reference_id=reference_id)
        except PayoutRequest.DoesNotExist:
            return None
    
    @staticmethod
    def generate_reference_id() -> str:
        """Generate unique payout reference ID"""
        date_str = timezone.now().strftime('%Y%m%d')
        unique_part = uuid.uuid4().hex[:8].upper()
        return f"PO-{date_str}-{unique_part}"
    
    @staticmethod
    def determine_payout_type(partner) -> str:
        """Determine payout type based on partner hierarchy"""
        if partner.is_franchise:
            return PayoutRequest.PayoutType.CHARGEGHAR_TO_FRANCHISE
        elif partner.is_vendor:
            if partner.is_chargeghar_level:
                return PayoutRequest.PayoutType.CHARGEGHAR_TO_VENDOR
            else:
                return PayoutRequest.PayoutType.FRANCHISE_TO_VENDOR
        return PayoutRequest.PayoutType.CHARGEGHAR_TO_VENDOR
    
    @staticmethod
    def create(
        partner_id: str,
        amount: Decimal,
        bank_name: Optional[str] = None,
        account_number: Optional[str] = None,
        account_holder_name: Optional[str] = None
    ) -> PayoutRequest:
        """Create a new payout request"""
        from api.partners.common.models import Partner
        
        partner = Partner.objects.get(id=partner_id)
        payout_type = PayoutRequestRepository.determine_payout_type(partner)
        reference_id = PayoutRequestRepository.generate_reference_id()
        
        return PayoutRequest.objects.create(
            partner_id=partner_id,
            payout_type=payout_type,
            amount=amount,
            net_amount=amount,  # No deductions - VAT already in balance
            vat_deducted=Decimal('0'),
            service_charge_deducted=Decimal('0'),
            bank_name=bank_name,
            account_number=account_number,
            account_holder_name=account_holder_name,
            reference_id=reference_id
        )
    
    @staticmethod
    def get_by_partner(
        partner_id: str,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> QuerySet:
        """Get payout requests for a partner"""
        queryset = PayoutRequest.objects.filter(
            partner_id=partner_id
        ).select_related('processed_by')
        
        if status:
            queryset = queryset.filter(status=status)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_pending_for_processor(payout_type: str) -> QuerySet:
        """Get pending payouts for a specific payout type"""
        return PayoutRequest.objects.filter(
            payout_type=payout_type,
            status=PayoutRequest.Status.PENDING
        ).select_related('partner', 'partner__parent').order_by('created_at')
    
    @staticmethod
    def get_franchise_vendor_payouts(franchise_id: str, status: Optional[str] = None) -> QuerySet:
        """Get payout requests from vendors under a franchise"""
        queryset = PayoutRequest.objects.filter(
            payout_type=PayoutRequest.PayoutType.FRANCHISE_TO_VENDOR,
            partner__parent_id=franchise_id
        ).select_related('partner')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def update_status(
        payout_id: str,
        status: str,
        processed_by_id: Optional[int] = None,
        rejection_reason: Optional[str] = None,
        admin_notes: Optional[str] = None
    ) -> Optional[PayoutRequest]:
        """Update payout request status"""
        try:
            payout = PayoutRequest.objects.get(id=payout_id)
            payout.status = status
            
            update_fields = ['status', 'updated_at']
            
            if processed_by_id:
                payout.processed_by_id = processed_by_id
                update_fields.append('processed_by_id')
            
            if status == PayoutRequest.Status.COMPLETED:
                payout.processed_at = timezone.now()
                update_fields.append('processed_at')
            
            if rejection_reason:
                payout.rejection_reason = rejection_reason
                update_fields.append('rejection_reason')
            
            if admin_notes:
                payout.admin_notes = admin_notes
                update_fields.append('admin_notes')
            
            payout.save(update_fields=update_fields)
            return payout
        except PayoutRequest.DoesNotExist:
            return None
    
    @staticmethod
    def get_summary_by_partner(
        partner_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """Get payout summary for a partner"""
        queryset = PayoutRequest.objects.filter(partner_id=partner_id)
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        total = queryset.aggregate(
            total_requests=Count('id'),
            total_amount=Sum('amount')
        )
        
        completed = queryset.filter(status=PayoutRequest.Status.COMPLETED).aggregate(
            completed_count=Count('id'),
            completed_amount=Sum('amount')
        )
        
        pending = queryset.filter(status=PayoutRequest.Status.PENDING).aggregate(
            pending_count=Count('id'),
            pending_amount=Sum('amount')
        )
        
        return {
            'total_requests': total['total_requests'] or 0,
            'total_amount': total['total_amount'] or Decimal('0'),
            'completed_count': completed['completed_count'] or 0,
            'completed_amount': completed['completed_amount'] or Decimal('0'),
            'pending_count': pending['pending_count'] or 0,
            'pending_amount': pending['pending_amount'] or Decimal('0')
        }
    
    @staticmethod
    def filter_payouts(
        payout_type: Optional[str] = None,
        status: Optional[str] = None,
        partner_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> QuerySet:
        """Filter payout requests with various criteria"""
        queryset = PayoutRequest.objects.select_related(
            'partner', 'partner__parent', 'processed_by'
        )
        
        if payout_type:
            queryset = queryset.filter(payout_type=payout_type)
        if status:
            queryset = queryset.filter(status=status)
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset.order_by('-created_at')
