"""
Franchise Vendor Service

Service layer for franchise vendor management operations.
"""

from decimal import Decimal
from typing import Dict, Optional

from django.db import transaction
from django.db.models import Q

from api.common.services.base import BaseService, ServiceException
from api.common.utils.pagination import paginate_queryset
from api.partners.common.models import Partner, StationDistribution, StationRevenueShare
from api.partners.common.repositories import (
    PartnerRepository,
    StationDistributionRepository,
    StationRevenueShareRepository,
)


class FranchiseVendorService(BaseService):
    """Service for franchise vendor operations"""
    
    @transaction.atomic
    def create_vendor(
        self,
        franchise: Partner,
        user_id: int,
        vendor_type: str,
        business_name: str,
        contact_phone: str,
        station_id: str,
        password: str,
        contact_email: Optional[str] = None,
        address: Optional[str] = None,
        revenue_model: Optional[str] = None,
        partner_percent: Optional[Decimal] = None,
        fixed_amount: Optional[Decimal] = None,
        notes: Optional[str] = None
    ) -> Partner:
        """
        Create a new vendor under franchise.
        
        Flow (same as admin):
        1. Create partner record with parent_id = franchise.id
        2. Set user.is_partner = True (for REVENUE vendors)
        3. Set user password (for REVENUE vendors)
        4. Assign station (FRANCHISE_TO_VENDOR)
        5. Create revenue share (for REVENUE vendors)
        
        Args:
            franchise: Franchise partner creating the vendor
            user_id: Existing user ID
            vendor_type: REVENUE or NON_REVENUE
            business_name: Vendor business name
            contact_phone: Contact phone
            station_id: Station UUID to assign (must be franchise's station)
            password: Initial password (required for REVENUE vendors)
            contact_email: Optional email
            address: Optional address
            revenue_model: PERCENTAGE or FIXED (required for REVENUE)
            partner_percent: % share (required if PERCENTAGE)
            fixed_amount: Fixed amount (required if FIXED)
            notes: Optional notes
            
        Returns:
            Created Partner instance
            
        Business Rules:
        - BR1.5: Franchise creates own vendors
        - BR2.2: Franchise assigns stations to vendors
        - BR2.3: Vendor can have ONLY ONE station
        - BR3.2: Franchise applies revenue model
        """
        from api.user.auth.models import User
        from api.user.stations.models import Station
        
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        # Verify station belongs to franchise
        station_owned = Station.objects.filter(
            id=station_id,
            partner_distributions__partner_id=franchise.id,
            partner_distributions__distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE,
            partner_distributions__is_active=True,
            is_deleted=False
        ).exists()
        
        if not station_owned:
            raise ServiceException(
                detail="Station not found or not owned by franchise",
                code="STATION_NOT_OWNED"
            )
        
        # Check if station already has vendor
        if StationDistributionRepository.station_has_operator(station_id):
            raise ServiceException(
                detail="Station already has a vendor assigned",
                code="STATION_ALREADY_ASSIGNED"
            )
        
        # Check if user already a partner
        if User.objects.filter(id=user_id, is_partner=True).exists():
            raise ServiceException(
                detail="User is already a partner",
                code="USER_ALREADY_PARTNER"
            )
        
        # Validate REVENUE vendor requirements
        if vendor_type == Partner.VendorType.REVENUE:
            if not password:
                raise ServiceException(
                    detail="Password required for REVENUE vendors",
                    code="PASSWORD_REQUIRED"
                )
            if not revenue_model:
                raise ServiceException(
                    detail="Revenue model required for REVENUE vendors",
                    code="REVENUE_MODEL_REQUIRED"
                )
            if revenue_model == 'PERCENTAGE' and not partner_percent:
                raise ServiceException(
                    detail="Partner percent required for PERCENTAGE model",
                    code="PARTNER_PERCENT_REQUIRED"
                )
            if revenue_model == 'FIXED' and not fixed_amount:
                raise ServiceException(
                    detail="Fixed amount required for FIXED model",
                    code="FIXED_AMOUNT_REQUIRED"
                )
        
        # Create partner with parent_id = franchise.id
        partner = PartnerRepository.create(
            user_id=user_id,
            partner_type=Partner.PartnerType.VENDOR,
            vendor_type=vendor_type,
            business_name=business_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            address=address,
            parent_id=str(franchise.id),  # Set parent to franchise
            assigned_by_id=franchise.user.id,
            notes=notes
        )
        
        # For REVENUE vendors: set is_partner and password
        if vendor_type == Partner.VendorType.REVENUE:
            user = User.objects.get(id=user_id)
            user.is_partner = True
            user.set_password(password)
            user.save(update_fields=['is_partner', 'password'])
        
        # Create station distribution (FRANCHISE_TO_VENDOR)
        distribution = StationDistributionRepository.create(
            station_id=station_id,
            partner_id=str(partner.id),
            distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR,
            assigned_by_id=franchise.user.id
        )
        
        # Create revenue share for REVENUE vendors
        if vendor_type == Partner.VendorType.REVENUE:
            StationRevenueShareRepository.create(
                distribution_id=str(distribution.id),
                revenue_model=revenue_model,
                partner_percent=float(partner_percent) if partner_percent else None,
                fixed_amount=float(fixed_amount) if fixed_amount else None
            )
        
        self.log_info(f"Vendor created: {partner.code} ({vendor_type}) by franchise {franchise.id}")
        return partner
    
    def get_vendors_list(self, franchise: Partner, filters: Dict) -> Dict:
        """
        Get paginated list of franchise's own vendors.
        
        Args:
            franchise: Partner object (must be FRANCHISE type)
            filters: Dict with page, page_size, vendor_type, status, search
            
        Returns:
            Dict with results, count, page, page_size, total_pages
            
        Business Rules:
        - BR10.2: Only own vendors (parent_id = franchise.id)
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        # Get vendors under this franchise
        queryset = Partner.objects.filter(
            parent_id=franchise.id,
            partner_type=Partner.PartnerType.VENDOR
        ).select_related('user').prefetch_related('station_distributions')
        
        # Apply filters
        if filters.get('vendor_type'):
            queryset = queryset.filter(vendor_type=filters['vendor_type'])
        
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('search'):
            search = filters['search']
            queryset = queryset.filter(
                Q(business_name__icontains=search) |
                Q(code__icontains=search) |
                Q(contact_phone__icontains=search)
            )
        
        # Paginate
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        
        paginated = paginate_queryset(queryset, page, page_size)
        
        # Build results
        results = []
        for vendor in paginated['results']:
            # Get station assignment
            station_dist = vendor.station_distributions.filter(
                distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR,
                is_active=True
            ).select_related('station').first()
            
            results.append({
                'id': vendor.id,
                'code': vendor.code,
                'business_name': vendor.business_name,
                'vendor_type': vendor.vendor_type,
                'contact_phone': vendor.contact_phone,
                'contact_email': vendor.contact_email,
                'status': vendor.status,
                'balance': vendor.balance,
                'total_earnings': vendor.total_earnings,
                'created_at': vendor.created_at,
                'station': {
                    'id': station_dist.station.id,
                    'station_name': station_dist.station.station_name,
                    'serial_number': station_dist.station.serial_number,
                    'address': station_dist.station.address,
                    'status': station_dist.station.status,
                } if station_dist else None
            })
        
        return {
            'results': results,
            'pagination': paginated['pagination']
        }
    
    def get_vendor_detail(self, franchise: Partner, vendor_id: str) -> Dict:
        """
        Get detailed vendor information.
        
        Args:
            franchise: Partner object (must be FRANCHISE type)
            vendor_id: Vendor UUID
            
        Returns:
            Dict with vendor details
            
        Business Rules:
        - BR10.2: Only own vendors (parent_id = franchise.id)
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        # Get vendor and verify ownership
        vendor = Partner.objects.filter(
            id=vendor_id,
            parent_id=franchise.id,
            partner_type=Partner.PartnerType.VENDOR
        ).select_related('user').first()
        
        if not vendor:
            raise ServiceException(
                detail="Vendor not found or access denied",
                code="VENDOR_NOT_FOUND"
            )
        
        # Get station assignment
        station_dist = StationDistribution.objects.filter(
            partner_id=vendor.id,
            distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR,
            is_active=True
        ).select_related('station').first()
        
        # Get revenue share
        revenue_share = None
        if vendor.vendor_type == Partner.VendorType.REVENUE and station_dist:
            share = StationRevenueShare.objects.filter(
                distribution_id=station_dist.id
            ).first()
            if share:
                revenue_share = {
                    'revenue_model': share.revenue_model,
                    'partner_percent': share.partner_percent,
                    'fixed_amount': share.fixed_amount,
                }
        
        return {
            'id': vendor.id,
            'code': vendor.code,
            'business_name': vendor.business_name,
            'vendor_type': vendor.vendor_type,
            'contact_phone': vendor.contact_phone,
            'contact_email': vendor.contact_email,
            'address': vendor.address,
            'status': vendor.status,
            'balance': vendor.balance,
            'total_earnings': vendor.total_earnings,
            'created_at': vendor.created_at,
            'updated_at': vendor.updated_at,
            'notes': vendor.notes,
            'user': {
                'id': vendor.user.id,
                'email': vendor.user.email,
                'username': vendor.user.username,
                'phone_number': vendor.user.phone_number,
            },
            'station': {
                'id': station_dist.station.id,
                'station_name': station_dist.station.station_name,
                'serial_number': station_dist.station.serial_number,
                'address': station_dist.station.address,
                'status': station_dist.station.status,
                'total_slots': station_dist.station.total_slots,
            } if station_dist else None,
            'revenue_share': revenue_share
        }
    
    @transaction.atomic
    def update_vendor(self, franchise: Partner, vendor_id: str, data: Dict) -> Partner:
        """
        Update vendor details.
        
        Args:
            franchise: Franchise partner
            vendor_id: Vendor UUID
            data: Dict with fields to update
            
        Returns:
            Updated Partner instance
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        vendor = Partner.objects.filter(
            id=vendor_id,
            parent_id=franchise.id,
            partner_type=Partner.PartnerType.VENDOR
        ).first()
        
        if not vendor:
            raise ServiceException(
                detail="Vendor not found or access denied",
                code="VENDOR_NOT_FOUND"
            )
        
        update_fields = ['updated_at']
        
        if 'business_name' in data:
            vendor.business_name = data['business_name']
            update_fields.append('business_name')
        
        if 'contact_phone' in data:
            vendor.contact_phone = data['contact_phone']
            update_fields.append('contact_phone')
        
        if 'contact_email' in data:
            vendor.contact_email = data['contact_email']
            update_fields.append('contact_email')
        
        if 'address' in data:
            vendor.address = data['address']
            update_fields.append('address')
        
        if 'notes' in data:
            vendor.notes = data['notes']
            update_fields.append('notes')
        
        vendor.save(update_fields=update_fields)
        return vendor
    
    @transaction.atomic
    def update_vendor_status(self, franchise: Partner, vendor_id: str, status: str, reason: str = None) -> Partner:
        """
        Update vendor status.
        
        Args:
            franchise: Franchise partner
            vendor_id: Vendor UUID
            status: New status (ACTIVE, INACTIVE, SUSPENDED)
            reason: Optional reason for status change
            
        Returns:
            Updated Partner instance
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        vendor = Partner.objects.filter(
            id=vendor_id,
            parent_id=franchise.id,
            partner_type=Partner.PartnerType.VENDOR
        ).first()
        
        if not vendor:
            raise ServiceException(
                detail="Vendor not found or access denied",
                code="VENDOR_NOT_FOUND"
            )
        
        old_status = vendor.status
        vendor.status = status
        
        if reason:
            status_note = f"\n[{franchise.user.username}] Status changed {old_status} → {status}: {reason}"
            vendor.notes = (vendor.notes or '') + status_note
            vendor.save(update_fields=['status', 'notes', 'updated_at'])
        else:
            vendor.save(update_fields=['status', 'updated_at'])
        
        self.log_info(f"Vendor status updated: {vendor.code} {old_status} → {status} by franchise {franchise.id}")
        return vendor
