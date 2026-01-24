# api/partners/auth/permissions.py
"""
Partner Permission Classes

Based on partners_auth.md and Business Rules BR9, BR10, BR12.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsPartner(BasePermission):
    """
    User is a partner (has partner_profile).
    
    Checks if user.partner_profile exists via OneToOne relation.
    """
    message = "User is not a partner."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return hasattr(request.user, 'partner_profile')


class IsActivePartner(BasePermission):
    """
    Partner account is ACTIVE.
    
    Combines authentication check + partner existence + active status.
    """
    message = "Partner account is not active."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'partner_profile'):
            return False
        return request.user.partner_profile.status == 'ACTIVE'


class IsFranchise(IsActivePartner):
    """
    Partner is a Franchise.
    
    Inherits IsActivePartner checks.
    BR10.2: Franchise has control over own vendors and stations.
    """
    message = "Access restricted to Franchise partners only."
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.partner_profile.partner_type == 'FRANCHISE'


class IsRevenueVendor(IsActivePartner):
    """
    Partner is a Revenue Vendor (has dashboard access).
    
    BR9.1-2: Revenue Vendors have dashboard access and receive earnings.
    """
    message = "Access restricted to Revenue Vendors only."
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        partner = request.user.partner_profile
        return (
            partner.partner_type == 'VENDOR' and
            partner.vendor_type == 'REVENUE'
        )


class IsVendor(IsActivePartner):
    """
    Partner is any Vendor type (Revenue or Non-Revenue).
    
    Used for IoT actions that both vendor types can perform (BR13.4).
    """
    message = "Access restricted to Vendor partners only."
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.partner_profile.partner_type == 'VENDOR'


class HasDashboardAccess(IsActivePartner):
    """
    Partner has dashboard access (Franchise OR Revenue Vendor).
    
    BR9.2: Revenue Vendors have dashboard access.
    BR9.4: Non-Revenue Vendors have NO dashboard access.
    
    Used for login and dashboard endpoints.
    """
    message = "You do not have dashboard access. Non-Revenue vendors cannot access the dashboard."
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        partner = request.user.partner_profile
        # Franchise always has access
        if partner.partner_type == 'FRANCHISE':
            return True
        # Revenue Vendor has access
        if partner.partner_type == 'VENDOR' and partner.vendor_type == 'REVENUE':
            return True
        return False


class CanManageVendors(IsFranchise):
    """
    Partner can manage vendors (create, update, suspend).
    
    Only Franchises can manage their own vendors (BR1.5, BR10.2).
    ChargeGhar admin manages CG-level vendors via admin endpoints.
    """
    message = "Only Franchises can manage vendors."
    
    def has_permission(self, request, view):
        return super().has_permission(request, view)


class CanViewOwnStation(IsActivePartner):
    """
    Partner can view their own station data.
    
    BR12.3: Revenue Vendor can view ONLY transactions from their assigned station.
    BR12.2: Franchise can view ONLY transactions from their own stations.
    """
    message = "You can only view your own station data."
    
    def has_permission(self, request, view):
        return super().has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        """
        Check if partner owns/operates the station.
        
        obj can be:
        - Station: Check via StationDistribution
        - StationDistribution: Check partner_id
        - RevenueDistribution: Check franchise_id or vendor_id
        """
        from api.partners.common.models import StationDistribution, Partner
        
        partner = request.user.partner_profile
        
        # If obj is a Station
        if hasattr(obj, 'partner_distributions'):
            return StationDistribution.objects.filter(
                station=obj,
                partner=partner,
                is_active=True
            ).exists()
        
        # If obj is StationDistribution
        if isinstance(obj, StationDistribution):
            return obj.partner_id == partner.id
        
        # If obj has franchise_id or vendor_id (RevenueDistribution)
        if hasattr(obj, 'franchise_id') and hasattr(obj, 'vendor_id'):
            if partner.partner_type == 'FRANCHISE':
                return obj.franchise_id == partner.id
            elif partner.partner_type == 'VENDOR':
                return obj.vendor_id == partner.id
        
        return False


class CanProcessPayout(IsActivePartner):
    """
    Partner can process payouts.
    
    BR8.1: ChargeGhar manages payouts to Franchises (admin endpoint).
    BR8.2: ChargeGhar manages payouts to CG-level Vendors (admin endpoint).
    BR8.3: Franchise manages payouts to their Vendors.
    """
    message = "You cannot process this payout."
    
    def has_object_permission(self, request, view, obj):
        """
        Check if partner can process the payout request.
        
        obj: PayoutRequest instance
        """
        partner = request.user.partner_profile
        
        # Franchise can only process FRANCHISE_TO_VENDOR payouts
        # for their own vendors
        if partner.partner_type == 'FRANCHISE':
            if obj.payout_type != 'FRANCHISE_TO_VENDOR':
                return False
            # Check if the payout requester is under this franchise
            return obj.partner.parent_id == partner.id
        
        return False


class CanPerformIotAction(IsActivePartner):
    """
    Partner can perform IoT actions on a station.
    
    BR13.4: Control rights based on partner type.
    - Franchise: Full access (EJECT, REBOOT, CHECK, WIFI, VOLUME, MODE)
    - Vendor: Limited (REBOOT, CHECK, WIFI, VOLUME, MODE) - No EJECT via IoT
    """
    message = "You cannot perform IoT actions on this station."
    
    # Actions vendors CAN perform
    VENDOR_ALLOWED_ACTIONS = ['REBOOT', 'CHECK', 'WIFI_SCAN', 'WIFI_CONNECT', 'VOLUME', 'MODE']
    
    # All actions (franchise can do all)
    ALL_ACTIONS = ['EJECT', 'REBOOT', 'CHECK', 'WIFI_SCAN', 'WIFI_CONNECT', 'VOLUME', 'MODE']
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        # Get action from request (view should set this or get from URL)
        action = getattr(view, 'iot_action', None)
        if not action:
            action = view.kwargs.get('action', '').upper()
        
        partner = request.user.partner_profile
        
        # Franchise can do all actions
        if partner.partner_type == 'FRANCHISE':
            return action in self.ALL_ACTIONS
        
        # Vendor can only do limited actions
        if partner.partner_type == 'VENDOR':
            return action in self.VENDOR_ALLOWED_ACTIONS
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """
        Check if partner has access to the specific station.
        
        obj: Station instance
        """
        from api.partners.common.models import StationDistribution
        
        partner = request.user.partner_profile
        
        # Check if partner operates this station
        distribution = StationDistribution.objects.filter(
            station=obj,
            partner=partner,
            is_active=True
        ).first()
        
        if distribution:
            return True
        
        # For Franchise: also check stations owned by them (CHARGEGHAR_TO_FRANCHISE)
        # and operated by their vendors
        if partner.partner_type == 'FRANCHISE':
            # Check ownership
            ownership = StationDistribution.objects.filter(
                station=obj,
                partner=partner,
                distribution_type='CHARGEGHAR_TO_FRANCHISE',
                is_active=True
            ).exists()
            if ownership:
                return True
            
            # Check if operated by their vendor
            vendor_operation = StationDistribution.objects.filter(
                station=obj,
                partner__parent=partner,
                distribution_type='FRANCHISE_TO_VENDOR',
                is_active=True
            ).exists()
            return vendor_operation
        
        return False
