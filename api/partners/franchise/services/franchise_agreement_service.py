"""
Franchise Agreement Service

Service layer for franchise agreement operations.
"""

from api.common.services.base import BaseService
from api.partners.common.models import Partner, StationDistribution, StationRevenueShare
from api.partners.common.repositories import PartnerRepository


class FranchiseAgreementService(BaseService):
    """Service for franchise agreement operations"""
    
    def get_agreements(self, franchise: Partner) -> dict:
        """
        Get franchise agreement with ChargeGhar and all vendor agreements.
        
        BR3.5: Franchise revenue share % with ChargeGhar
        BR3.3: Vendor revenue model (Fixed OR Percentage)
        BR3.4: Non-Revenue vendors have no revenue model
        """
        # Franchise agreement with ChargeGhar
        franchise_agreement = {
            'franchise_id': franchise.id,
            'franchise_code': franchise.code,
            'franchise_name': franchise.business_name,
            'revenue_share_percent': franchise.revenue_share_percent,
            'upfront_payment': franchise.upfront_amount,
            'balance': franchise.balance,
            'total_earnings': franchise.total_earnings,
            'total_stations': StationDistribution.objects.filter(
                partner=franchise,
                is_active=True
            ).count(),
            'total_vendors': Partner.objects.filter(parent=franchise).count(),
            'created_at': franchise.created_at,
        }
        
        # Vendor agreements
        vendors = PartnerRepository.get_vendors_under_franchise(str(franchise.id))
        vendor_agreements = []
        
        for vendor in vendors:
            # Get station distribution
            distribution = StationDistribution.objects.filter(partner=vendor).first()
            
            agreement = {
                'vendor_id': vendor.id,
                'vendor_code': vendor.code,
                'vendor_name': vendor.business_name,
                'vendor_type': vendor.vendor_type,
                'station_id': distribution.station.id if distribution else None,
                'station_name': distribution.station.station_name if distribution else None,
                'station_code': distribution.station.serial_number if distribution else None,
                'revenue_model': None,
                'partner_percent': None,
                'fixed_amount': None,
                'is_active': vendor.status == 'ACTIVE',
                'created_at': vendor.created_at,
            }
            
            # Get revenue share if exists (only for REVENUE vendors)
            if distribution and vendor.vendor_type == 'REVENUE':
                try:
                    revenue_share = StationRevenueShare.objects.get(distribution=distribution)
                    agreement['revenue_model'] = revenue_share.revenue_model
                    agreement['partner_percent'] = revenue_share.partner_percent
                    agreement['fixed_amount'] = revenue_share.fixed_amount
                except StationRevenueShare.DoesNotExist:
                    pass
            
            vendor_agreements.append(agreement)
        
        return {
            'franchise_agreement': franchise_agreement,
            'vendor_agreements': vendor_agreements
        }
