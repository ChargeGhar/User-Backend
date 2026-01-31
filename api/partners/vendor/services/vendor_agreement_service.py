"""
Vendor Agreement Service

Handles vendor agreement operations.
"""

from rest_framework.exceptions import PermissionDenied

from api.partners.common.repositories import (
    PartnerRepository,
    StationDistributionRepository
)


class VendorAgreementService:
    """Service for vendor agreement operations"""
    
    @staticmethod
    def get_agreement(vendor_id: str) -> dict:
        """
        Get vendor's revenue agreement.
        
        BR2.3: Single station
        BR3.4: Revenue vendors only
        """
        # Get vendor
        vendor = PartnerRepository.get_by_id(vendor_id)
        if not vendor:
            raise ValueError("Vendor not found")
        
        # Validate: Revenue vendor only
        if not vendor.is_revenue_vendor:
            raise PermissionDenied("Non-revenue vendors have no agreement")
        
        # Get vendor's station distribution (BR2.3 - single station)
        distribution = StationDistributionRepository.get_active_by_partner(vendor_id).first()
        
        if not distribution:
            raise ValueError("No active station assignment found")
        
        # Get revenue model
        revenue_share = distribution.revenue_share if hasattr(distribution, 'revenue_share') else None
        
        if not revenue_share:
            raise ValueError("No revenue model configured")
        
        # Build response
        return {
            'vendor': {
                'id': str(vendor.id),
                'code': vendor.code,
                'business_name': vendor.business_name,
                'vendor_type': vendor.vendor_type,
                'status': vendor.status,
                'balance': vendor.balance,
                'total_earnings': vendor.total_earnings
            },
            'parent': {
                'id': str(vendor.parent.id),
                'code': vendor.parent.code,
                'business_name': vendor.parent.business_name,
                'partner_type': vendor.parent.partner_type
            } if vendor.parent else None,
            'station': {
                'id': str(distribution.station.id),
                'name': distribution.station.station_name,
                'code': distribution.station.serial_number,
                'address': distribution.station.address,
                'total_slots': distribution.station.total_slots
            },
            'distribution': {
                'distribution_type': distribution.distribution_type,
                'effective_date': distribution.effective_date,
                'is_active': distribution.is_active
            },
            'revenue_model': {
                'model_type': revenue_share.revenue_model,
                'partner_percent': revenue_share.partner_percent,
                'fixed_amount': revenue_share.fixed_amount,
                'description': VendorAgreementService._get_revenue_description(revenue_share)
            }
        }
    
    @staticmethod
    def _get_revenue_description(revenue_share) -> str:
        """Generate human-readable revenue model description"""
        if revenue_share.revenue_model == 'PERCENTAGE':
            return f"You receive {revenue_share.partner_percent}% of net revenue from this station"
        else:  # FIXED
            return f"You pay NPR {revenue_share.fixed_amount} monthly to the station owner"
