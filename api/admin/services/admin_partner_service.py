# api/admin/services/admin_partner_service.py
"""
Admin Partner Service

Service layer for admin partner management operations.
Based on Endpoints.md Section 1.1-1.5
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

from django.db import transaction
from django.core.paginator import Paginator

from api.common.services.base import BaseService, ServiceException
from api.partners.common.models import Partner, StationDistribution, StationRevenueShare, PayoutRequest
from api.partners.common.repositories import (
    PartnerRepository,
    StationDistributionRepository,
    StationRevenueShareRepository,
    PayoutRequestRepository,
)


logger = logging.getLogger(__name__)


class AdminPartnerService(BaseService):
    """
    Admin service for partner management.
    
    Handles:
    - Partner CRUD (Franchise & Vendor)
    - Station distributions
    - Payout management
    """
    
    # ========================================================================
    # Partner Management (Section 1.1)
    # ========================================================================
    
    def get_partners_list(self, filters: Dict) -> Dict:
        """
        Get paginated list of all partners with filters.
        
        Args:
            filters: Dict with partner_type, vendor_type, status, parent_id, search, page, page_size
            
        Returns:
            Dict with results, count, page, page_size, total_pages
        """
        queryset = PartnerRepository.filter_partners(
            partner_type=filters.get('partner_type'),
            vendor_type=filters.get('vendor_type'),
            status=filters.get('status'),
            parent_id=filters.get('parent_id'),
            search=filters.get('search')
        )
        
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 20)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'results': list(page_obj.object_list),
            'count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages
        }
    
    def get_partner_detail(self, partner_id: str) -> Partner:
        """
        Get partner details by ID.
        
        Args:
            partner_id: Partner UUID
            
        Returns:
            Partner instance
            
        Raises:
            ServiceException: If partner not found
        """
        partner = PartnerRepository.get_by_id(partner_id)
        if not partner:
            raise ServiceException(
                detail="Partner not found",
                code="PARTNER_NOT_FOUND"
            )
        return partner
    
    @transaction.atomic
    def create_franchise(
        self,
        user_id: int,
        business_name: str,
        contact_phone: str,
        revenue_share_percent: Decimal,
        password: str,
        admin_user,
        contact_email: Optional[str] = None,
        address: Optional[str] = None,
        upfront_amount: Decimal = Decimal('0'),
        station_ids: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Partner:
        """
        Create a new franchise partner.
        
        Flow:
        1. Create partner record
        2. Set user.is_partner = True
        3. Set user password
        4. Assign stationss (if provided)
        
        Args:
            user_id: Existing user ID
            business_name: Franchise business name
            contact_phone: Contact phone
            revenue_share_percent: Franchise's % share (y%)
            password: Initial password for dashboard login
            admin_user: Admin user creating the partner
            contact_email: Optional email
            address: Optional address
            upfront_amount: One-time payment received
            station_ids: List of station UUIDs to assign
            notes: Optional notes
            
        Returns:
            Created Partner instance
        """
        from api.user.auth.models import User
        
        # Create partner
        partner = PartnerRepository.create(
            user_id=user_id,
            partner_type=Partner.PartnerType.FRANCHISE,
            business_name=business_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            address=address,
            upfront_amount=float(upfront_amount),
            revenue_share_percent=float(revenue_share_percent),
            assigned_by_id=admin_user.id,
            notes=notes
        )
        
        # Update user: set is_partner and password
        user = User.objects.get(id=user_id)
        user.is_partner = True
        user.set_password(password)
        user.save(update_fields=['is_partner', 'password'])
        
        # Assign stations to franchise
        if station_ids:
            for station_id in station_ids:
                StationDistributionRepository.create(
                    station_id=str(station_id),
                    partner_id=str(partner.id),
                    distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE,
                    assigned_by_id=admin_user.id
                )
        
        self.log_info(f"Franchise created: {partner.code} by admin {admin_user.id}")
        return partner
    
    @transaction.atomic
    def create_vendor(
        self,
        user_id: int,
        vendor_type: str,
        business_name: str,
        contact_phone: str,
        station_ids: List[str],
        admin_user,
        contact_email: Optional[str] = None,
        address: Optional[str] = None,
        revenue_model: Optional[str] = None,
        partner_percent: Optional[Decimal] = None,
        fixed_amount: Optional[Decimal] = None,
        password: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Partner:
        """
        Create a new vendor partner (ChargeGhar-level).
        
        Flow:
        1. Create partner record
        2. Set user.is_partner = True (for REVENUE vendors)
        3. Set user password (for REVENUE vendors)
        4. Assign stations
        5. Create revenue share for each station (for REVENUE vendors)
        
        Args:
            user_id: Existing user ID
            vendor_type: REVENUE or NON_REVENUE
            business_name: Vendor business name
            contact_phone: Contact phone
            station_ids: List of Station UUIDs to assign
            admin_user: Admin user creating the partner
            contact_email: Optional email
            address: Optional address
            revenue_model: PERCENTAGE or FIXED (required for REVENUE)
            partner_percent: % share (required if PERCENTAGE)
            fixed_amount: Fixed amount (required if FIXED)
            password: Initial password (required for REVENUE)
            notes: Optional notes
            
        Returns:
            Created Partner instance
        """
        from api.user.auth.models import User
        
        # Create partner
        partner = PartnerRepository.create(
            user_id=user_id,
            partner_type=Partner.PartnerType.VENDOR,
            vendor_type=vendor_type,
            business_name=business_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            address=address,
            assigned_by_id=admin_user.id,
            notes=notes
        )
        
        # For REVENUE vendors: set is_partner and password
        if vendor_type == Partner.VendorType.REVENUE:
            user = User.objects.get(id=user_id)
            user.is_partner = True
            user.set_password(password)
            user.save(update_fields=['is_partner', 'password'])
        
        # Create station distributions for all stations
        for station_id in station_ids:
            distribution = StationDistributionRepository.create(
                station_id=str(station_id),
                partner_id=str(partner.id),
                distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_VENDOR,
                assigned_by_id=admin_user.id
            )

            # Create revenue share for REVENUE vendors (same config for all stations)
            if vendor_type == Partner.VendorType.REVENUE:
                StationRevenueShareRepository.create(
                    distribution_id=str(distribution.id),
                    revenue_model=revenue_model,
                    partner_percent=float(partner_percent) if partner_percent else None,
                    fixed_amount=float(fixed_amount) if fixed_amount else None
                )

        self.log_info(f"Vendor created: {partner.code} ({vendor_type}) with {len(station_ids)} stations by admin {admin_user.id}")
        return partner

    @transaction.atomic
    def assign_stations_to_vendor(
        self,
        vendor_id: str,
        station_ids: List[str],
        admin_user,
        notes: Optional[str] = None
    ) -> List:
        """
        Assign additional stations to an existing vendor.
        Copies the vendor's existing revenue configuration to new stations.

        Args:
            vendor_id: Vendor Partner UUID
            station_ids: List of Station UUIDs to assign
            admin_user: Admin user making the assignment
            notes: Optional notes

        Returns:
            List of created StationDistribution instances
        """
        from api.partners.common.services.station_assignment_service import StationAssignmentService

        service = StationAssignmentService()
        results = service.assign_stations_to_vendor(
            partner_id=vendor_id,
            station_ids=station_ids,
            assigned_by_id=admin_user.id,
            distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_VENDOR,
            notes=notes
        )

        distributions = [r['distribution'] for r in results]
        self.log_info(
            f"Assigned {len(distributions)} stations to vendor {vendor_id} by admin {admin_user.id}"
        )
        return distributions

    @transaction.atomic
    def update_partner(self, partner_id: str, data: Dict, admin_user) -> Partner:
        """
        Update partner details.
        
        Args:
            partner_id: Partner UUID
            data: Dict with fields to update
            admin_user: Admin user making the update
            
        Returns:
            Updated Partner instance
        """
        partner = self.get_partner_detail(partner_id)
        
        # Update allowed fields
        update_fields = ['updated_at']
        
        if 'business_name' in data:
            partner.business_name = data['business_name']
            update_fields.append('business_name')
        
        if 'contact_phone' in data:
            partner.contact_phone = data['contact_phone']
            update_fields.append('contact_phone')
        
        if 'contact_email' in data:
            partner.contact_email = data['contact_email']
            update_fields.append('contact_email')
        
        if 'address' in data:
            partner.address = data['address']
            update_fields.append('address')

        if 'subject' in data:
            partner.subject = data['subject']
            update_fields.append('subject')

        if 'message' in data:
            partner.message = data['message']
            update_fields.append('message')
        
        if 'notes' in data:
            partner.notes = data['notes']
            update_fields.append('notes')
        
        # Franchise-specific fields
        if partner.is_franchise:
            if 'upfront_amount' in data:
                partner.upfront_amount = data['upfront_amount']
                update_fields.append('upfront_amount')
            
            if 'revenue_share_percent' in data:
                partner.revenue_share_percent = data['revenue_share_percent']
                update_fields.append('revenue_share_percent')
        
        partner.save(update_fields=update_fields)
        
        self.log_info(f"Partner updated: {partner.code} by admin {admin_user.id}")
        return partner
    
    @transaction.atomic
    def update_partner_status(
        self,
        partner_id: str,
        status: str,
        admin_user,
        reason: Optional[str] = None
    ) -> Partner:
        """
        Update partner status (activate/suspend).
        
        Args:
            partner_id: Partner UUID
            status: New status (ACTIVE, INACTIVE, SUSPENDED)
            admin_user: Admin user making the change
            reason: Optional reason for status change
            
        Returns:
            Updated Partner instance
        """
        partner = self.get_partner_detail(partner_id)
        old_status = partner.status
        
        partner.status = status
        
        # Append reason to notes
        if reason:
            status_note = f"\n[{admin_user.username}] Status changed {old_status} → {status}: {reason}"
            partner.notes = (partner.notes or '') + status_note
            partner.save(update_fields=['status', 'notes', 'updated_at'])
        else:
            partner.save(update_fields=['status', 'updated_at'])
        
        self.log_info(f"Partner status updated: {partner.code} {old_status} → {status} by admin {admin_user.id}")
        return partner
    
    @transaction.atomic
    def reset_partner_password(
        self,
        partner_id: str,
        new_password: str,
        admin_user
    ) -> Partner:
        """
        Reset partner password (admin action).
        
        Used when partner forgets password and contacts admin.
        
        Args:
            partner_id: Partner UUID
            new_password: New password to set
            admin_user: Admin user performing the reset
            
        Returns:
            Partner instance
            
        Raises:
            ServiceException: If partner not found or has no dashboard access
        """
        from api.user.auth.models import User
        
        partner = self.get_partner_detail(partner_id)
        
        # Verify partner has dashboard access (only FRANCHISE or REVENUE vendors)
        if not partner.has_dashboard_access:
            raise ServiceException(
                detail="Cannot reset password for partner without dashboard access",
                code="NO_DASHBOARD_ACCESS"
            )
        
        # Get user and verify is_partner flag
        user = partner.user
        if not user.is_partner:
            # This shouldn't happen but handle it gracefully
            user.is_partner = True
        
        # Set new password
        user.set_password(new_password)
        user.save(update_fields=['is_partner', 'password'])
        
        # Add note to partner record
        reset_note = f"\n[{admin_user.username}] Password reset by admin"
        partner.notes = (partner.notes or '') + reset_note
        partner.save(update_fields=['notes', 'updated_at'])
        
        self.log_info(f"Password reset for partner: {partner.code} by admin {admin_user.id}")
        return partner
    
    @transaction.atomic
    def change_vendor_type(
        self,
        partner_id: str,
        new_vendor_type: str,
        admin_user,
        password: Optional[str] = None,
        revenue_model: Optional[str] = None,
        partner_percent: Optional[Decimal] = None,
        fixed_amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Partner:
        """
        Change vendor type (NON_REVENUE <-> REVENUE).
        
        NON_REVENUE → REVENUE:
        1. Set user.is_partner = True
        2. Set password
        3. Create revenue share
        
        REVENUE → NON_REVENUE:
        1. Keep user.is_partner = True (but permission blocks dashboard access)
        2. Delete revenue share
        
        Args:
            partner_id: Partner UUID
            new_vendor_type: New vendor type (REVENUE or NON_REVENUE)
            admin_user: Admin user making the change
            password: Required when changing to REVENUE
            revenue_model: Required when changing to REVENUE
            partner_percent: Required if revenue_model=PERCENTAGE
            fixed_amount: Required if revenue_model=FIXED
            reason: Optional reason for change
            
        Returns:
            Updated Partner instance
        """
        from api.user.auth.models import User
        
        partner = self.get_partner_detail(partner_id)
        
        # Verify this is a vendor
        if not partner.is_vendor:
            raise ServiceException(
                detail="Can only change vendor type for VENDOR partners",
                code="NOT_A_VENDOR"
            )
        
        old_vendor_type = partner.vendor_type
        
        # Check if actually changing
        if old_vendor_type == new_vendor_type:
            raise ServiceException(
                detail=f"Vendor is already {new_vendor_type}",
                code="NO_CHANGE"
            )
        
        # Get user
        user = partner.user
        
        if new_vendor_type == Partner.VendorType.REVENUE:
            # NON_REVENUE → REVENUE
            # 1. Enable dashboard access
            user.is_partner = True
            user.set_password(password)
            user.save(update_fields=['is_partner', 'password'])
            
            # 2. Create revenue share for existing station distribution
            distribution = StationDistributionRepository.get_active_by_partner(str(partner.id)).first()
            if distribution:
                # Check if revenue share already exists (shouldn't but be safe)
                existing_share = StationRevenueShareRepository.get_by_distribution_id(str(distribution.id))
                if existing_share:
                    # Update existing
                    StationRevenueShareRepository.update(
                        share_id=str(existing_share.id),
                        revenue_model=revenue_model,
                        partner_percent=float(partner_percent) if partner_percent else None,
                        fixed_amount=float(fixed_amount) if fixed_amount else None
                    )
                else:
                    # Create new
                    StationRevenueShareRepository.create(
                        distribution_id=str(distribution.id),
                        revenue_model=revenue_model,
                        partner_percent=float(partner_percent) if partner_percent else None,
                        fixed_amount=float(fixed_amount) if fixed_amount else None
                    )
            
        else:
            # REVENUE → NON_REVENUE
            # 1. Keep is_partner = True (permission class handles access)
            # Note: We don't remove password - just permission blocks dashboard
            
            # 2. Delete revenue share
            StationRevenueShareRepository.delete_by_partner_id(str(partner.id))
        
        # Update partner vendor_type
        partner.vendor_type = new_vendor_type
        
        # Add note
        change_note = f"\n[{admin_user.username}] Vendor type changed {old_vendor_type} → {new_vendor_type}"
        if reason:
            change_note += f": {reason}"
        partner.notes = (partner.notes or '') + change_note
        
        partner.save(update_fields=['vendor_type', 'notes', 'updated_at'])
        
        self.log_info(
            f"Vendor type changed: {partner.code} {old_vendor_type} → {new_vendor_type} "
            f"by admin {admin_user.id}"
        )
        return partner
    
    # ========================================================================
    # Station Distribution (Section 1.2)
    # ========================================================================
    
    def get_station_distributions(self, filters: Dict) -> Dict:
        """
        Get paginated list of station distributions.
        
        Args:
            filters: Dict with station_id, partner_id, distribution_type, is_active, page, page_size
            
        Returns:
            Dict with results, count, page, page_size, total_pages
        """
        queryset = StationDistributionRepository.filter_distributions(
            station_id=filters.get('station_id'),
            partner_id=filters.get('partner_id'),
            distribution_type=filters.get('distribution_type'),
            is_active=filters.get('is_active')
        )
        
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 20)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'results': list(page_obj.object_list),
            'count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages
        }
    
    def get_available_stations(self) -> List:
        """
        Get stations not assigned to any partner.
        
        Returns:
            List of unassigned stations
        """
        return list(StationDistributionRepository.get_unassigned_stations())
    
    @transaction.atomic
    def deactivate_station_distribution(self, distribution_id: str, admin_user) -> StationDistribution:
        """
        Deactivate a station distribution.
        
        Args:
            distribution_id: Distribution UUID
            admin_user: Admin user making the change
            
        Returns:
            Deactivated StationDistribution instance
        """
        distribution = StationDistributionRepository.get_by_id(distribution_id)
        if not distribution:
            raise ServiceException(
                detail="Station distribution not found",
                code="DISTRIBUTION_NOT_FOUND"
            )
        
        if not distribution.is_active:
            raise ServiceException(
                detail="Distribution is already inactive",
                code="ALREADY_INACTIVE"
            )
        
        # Deactivate distribution
        distribution = StationDistributionRepository.deactivate(distribution_id)
        
        # Also delete revenue share if exists
        StationRevenueShareRepository.delete_by_distribution_id(distribution_id)
        
        self.log_info(
            f"Distribution deactivated: {distribution_id} "
            f"(station: {distribution.station_id}, partner: {distribution.partner.code}) "
            f"by admin {admin_user.id}"
        )
        return distribution
    
    # ========================================================================
    # Payout Management (Section 1.4)
    # ========================================================================
    
    def get_payouts_list(self, filters: Dict) -> Dict:
        """
        Get paginated list of payout requests.
        
        Args:
            filters: Dict with payout_type, status, partner_id, page, page_size
            
        Returns:
            Dict with results, count, page, page_size, total_pages
        """
        queryset = PayoutRequestRepository.filter_payouts(
            payout_type=filters.get('payout_type'),
            status=filters.get('status'),
            partner_id=filters.get('partner_id')
        )
        
        # Admin only sees CHARGEGHAR_TO_FRANCHISE and CHARGEGHAR_TO_VENDOR
        queryset = queryset.filter(
            payout_type__in=[
                PayoutRequest.PayoutType.CHARGEGHAR_TO_FRANCHISE,
                PayoutRequest.PayoutType.CHARGEGHAR_TO_VENDOR
            ]
        )
        
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 20)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'results': list(page_obj.object_list),
            'count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages
        }
    
    def get_payout_detail(self, payout_id: str) -> PayoutRequest:
        """
        Get payout details by ID.
        
        Args:
            payout_id: Payout UUID
            
        Returns:
            PayoutRequest instance
        """
        payout = PayoutRequestRepository.get_by_id(payout_id)
        if not payout:
            raise ServiceException(
                detail="Payout request not found",
                code="PAYOUT_NOT_FOUND"
            )
        
        # Admin can only view CG payouts
        if payout.payout_type not in [
            PayoutRequest.PayoutType.CHARGEGHAR_TO_FRANCHISE,
            PayoutRequest.PayoutType.CHARGEGHAR_TO_VENDOR
        ]:
            raise ServiceException(
                detail="Access denied to this payout type",
                code="ACCESS_DENIED"
            )
        
        return payout
    
    @transaction.atomic
    def approve_payout(self, payout_id: str, admin_user, admin_notes: Optional[str] = None) -> PayoutRequest:
        """
        Approve a pending payout request.
        
        Args:
            payout_id: Payout UUID
            admin_user: Admin user approving
            admin_notes: Optional notes
            
        Returns:
            Updated PayoutRequest instance
        """
        payout = self.get_payout_detail(payout_id)
        
        if payout.status != PayoutRequest.Status.PENDING:
            raise ServiceException(
                detail=f"Cannot approve payout with status {payout.status}",
                code="INVALID_STATUS"
            )
        
        payout = PayoutRequestRepository.update_status(
            payout_id=payout_id,
            status=PayoutRequest.Status.APPROVED,
            processed_by_id=admin_user.id,
            admin_notes=admin_notes
        )
        
        self.log_info(f"Payout approved: {payout.reference_id} by admin {admin_user.id}")
        return payout
    
    @transaction.atomic
    def process_payout(self, payout_id: str, admin_user, admin_notes: Optional[str] = None) -> PayoutRequest:
        """
        Mark payout as processing.
        
        Args:
            payout_id: Payout UUID
            admin_user: Admin user processing
            admin_notes: Optional notes
            
        Returns:
            Updated PayoutRequest instance
        """
        payout = self.get_payout_detail(payout_id)
        
        if payout.status != PayoutRequest.Status.APPROVED:
            raise ServiceException(
                detail=f"Cannot process payout with status {payout.status}",
                code="INVALID_STATUS"
            )
        
        payout = PayoutRequestRepository.update_status(
            payout_id=payout_id,
            status=PayoutRequest.Status.PROCESSING,
            processed_by_id=admin_user.id,
            admin_notes=admin_notes
        )
        
        self.log_info(f"Payout processing: {payout.reference_id} by admin {admin_user.id}")
        return payout
    
    @transaction.atomic
    def complete_payout(self, payout_id: str, admin_user, admin_notes: Optional[str] = None) -> PayoutRequest:
        """
        Complete a payout and deduct from partner balance.
        
        Args:
            payout_id: Payout UUID
            admin_user: Admin user completing
            admin_notes: Optional notes
            
        Returns:
            Updated PayoutRequest instance
        """
        payout = self.get_payout_detail(payout_id)
        
        if payout.status != PayoutRequest.Status.PROCESSING:
            raise ServiceException(
                detail=f"Cannot complete payout with status {payout.status}",
                code="INVALID_STATUS"
            )
        
        # Deduct from partner balance
        PartnerRepository.update_balance(
            partner_id=str(payout.partner_id),
            amount=float(payout.amount),
            add=False
        )
        
        # Update payout status
        payout = PayoutRequestRepository.update_status(
            payout_id=payout_id,
            status=PayoutRequest.Status.COMPLETED,
            processed_by_id=admin_user.id,
            admin_notes=admin_notes
        )
        
        self.log_info(f"Payout completed: {payout.reference_id} amount {payout.amount} by admin {admin_user.id}")
        return payout
    
    @transaction.atomic
    def reject_payout(
        self,
        payout_id: str,
        admin_user,
        rejection_reason: str,
        admin_notes: Optional[str] = None
    ) -> PayoutRequest:
        """
        Reject a payout request.
        
        Args:
            payout_id: Payout UUID
            admin_user: Admin user rejecting
            rejection_reason: Reason for rejection
            admin_notes: Optional notes
            
        Returns:
            Updated PayoutRequest instance
        """
        payout = self.get_payout_detail(payout_id)
        
        if payout.status not in [PayoutRequest.Status.PENDING, PayoutRequest.Status.APPROVED]:
            raise ServiceException(
                detail=f"Cannot reject payout with status {payout.status}",
                code="INVALID_STATUS"
            )
        
        payout = PayoutRequestRepository.update_status(
            payout_id=payout_id,
            status=PayoutRequest.Status.REJECTED,
            processed_by_id=admin_user.id,
            rejection_reason=rejection_reason,
            admin_notes=admin_notes
        )
        
        self.log_info(f"Payout rejected: {payout.reference_id} by admin {admin_user.id}")
        return payout
