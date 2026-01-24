from typing import Optional, List
from django.db.models import QuerySet

from api.partners.common.models import Partner


class PartnerRepository:
    """
    Repository for Partner model database operations.
    """
    
    @staticmethod
    def get_by_id(partner_id: str) -> Optional[Partner]:
        """Get partner by ID"""
        try:
            return Partner.objects.select_related('user', 'parent').get(id=partner_id)
        except Partner.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_user_id(user_id: int) -> Optional[Partner]:
        """Get partner by user ID"""
        try:
            return Partner.objects.select_related('user', 'parent').get(user_id=user_id)
        except Partner.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_code(code: str) -> Optional[Partner]:
        """Get partner by code"""
        try:
            return Partner.objects.select_related('user', 'parent').get(code=code)
        except Partner.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_active() -> QuerySet:
        """Get all active partners"""
        return Partner.objects.filter(
            status=Partner.Status.ACTIVE
        ).select_related('user', 'parent')
    
    @staticmethod
    def get_franchises() -> QuerySet:
        """Get all franchises"""
        return Partner.objects.filter(
            partner_type=Partner.PartnerType.FRANCHISE
        ).select_related('user')
    
    @staticmethod
    def get_active_franchises() -> QuerySet:
        """Get all active franchises"""
        return Partner.objects.filter(
            partner_type=Partner.PartnerType.FRANCHISE,
            status=Partner.Status.ACTIVE
        ).select_related('user')
    
    @staticmethod
    def get_vendors_under_chargeghar() -> QuerySet:
        """Get all vendors directly under ChargeGhar (parent_id = NULL)"""
        return Partner.objects.filter(
            partner_type=Partner.PartnerType.VENDOR,
            parent__isnull=True
        ).select_related('user')
    
    @staticmethod
    def get_vendors_under_franchise(franchise_id: str) -> QuerySet:
        """Get all vendors under a specific franchise"""
        return Partner.objects.filter(
            partner_type=Partner.PartnerType.VENDOR,
            parent_id=franchise_id
        ).select_related('user', 'parent')
    
    @staticmethod
    def get_child_partners(partner_id: str) -> QuerySet:
        """Get all child partners (vendors) under a partner"""
        return Partner.objects.filter(
            parent_id=partner_id
        ).select_related('user')
    
    @staticmethod
    def generate_partner_code(partner_type: str) -> str:
        """
        Generate unique partner code.
        
        Format: FR-001 for Franchise, VN-001 for Vendor
        """
        prefix = 'FR' if partner_type == Partner.PartnerType.FRANCHISE else 'VN'
        
        last_partner = Partner.objects.filter(
            code__startswith=prefix
        ).order_by('-code').first()
        
        if last_partner:
            try:
                last_num = int(last_partner.code.split('-')[1])
                new_num = last_num + 1
            except (IndexError, ValueError):
                new_num = 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:03d}"
    
    @staticmethod
    def user_is_already_partner(user_id: int) -> bool:
        """Check if user is already a partner"""
        return Partner.objects.filter(user_id=user_id).exists()
    
    @staticmethod
    def create(
        user_id: int,
        partner_type: str,
        business_name: str,
        contact_phone: str,
        assigned_by_id: int,
        vendor_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        contact_email: Optional[str] = None,
        address: Optional[str] = None,
        upfront_amount: float = 0,
        revenue_share_percent: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Partner:
        """Create a new partner"""
        code = PartnerRepository.generate_partner_code(partner_type)
        
        return Partner.objects.create(
            user_id=user_id,
            partner_type=partner_type,
            vendor_type=vendor_type,
            parent_id=parent_id,
            code=code,
            business_name=business_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            address=address,
            upfront_amount=upfront_amount,
            revenue_share_percent=revenue_share_percent,
            assigned_by_id=assigned_by_id,
            notes=notes
        )
    
    @staticmethod
    def update_status(partner_id: str, status: str) -> Optional[Partner]:
        """Update partner status"""
        try:
            partner = Partner.objects.get(id=partner_id)
            partner.status = status
            partner.save(update_fields=['status', 'updated_at'])
            return partner
        except Partner.DoesNotExist:
            return None
    
    @staticmethod
    def update_balance(partner_id: str, amount: float, add: bool = True) -> Optional[Partner]:
        """
        Update partner balance.
        
        Args:
            partner_id: Partner ID
            amount: Amount to add/subtract
            add: True to add, False to subtract
        """
        from django.db.models import F
        
        if add:
            Partner.objects.filter(id=partner_id).update(
                balance=F('balance') + amount,
                total_earnings=F('total_earnings') + amount
            )
        else:
            Partner.objects.filter(id=partner_id).update(
                balance=F('balance') - amount
            )
        
        return PartnerRepository.get_by_id(partner_id)
    
    @staticmethod
    def filter_partners(
        partner_type: Optional[str] = None,
        vendor_type: Optional[str] = None,
        status: Optional[str] = None,
        parent_id: Optional[str] = None,
        search: Optional[str] = None
    ) -> QuerySet:
        """
        Filter partners with various criteria.
        """
        queryset = Partner.objects.select_related('user', 'parent')
        
        if partner_type:
            queryset = queryset.filter(partner_type=partner_type)
        
        if vendor_type:
            queryset = queryset.filter(vendor_type=vendor_type)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        elif parent_id == '':
            # Explicitly filter for ChargeGhar-level
            queryset = queryset.filter(parent__isnull=True)
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(business_name__icontains=search) |
                Q(contact_phone__icontains=search) |
                Q(contact_email__icontains=search)
            )
        
        return queryset.order_by('-created_at')
