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

        BR2.3: Vendor can have MULTIPLE stations (updated)
        BR3.4: Revenue vendors only
        """
        # Get vendor
        vendor = PartnerRepository.get_by_id(vendor_id)
        if not vendor:
            raise ValueError("Vendor not found")

        # Validate: Revenue vendor only
        if not vendor.is_revenue_vendor:
            raise PermissionDenied("Non-revenue vendors have no agreement")

        # Get all vendor station distributions (updated for multi-station)
        distributions = StationDistributionRepository.get_active_by_partner(vendor_id)

        if not distributions:
            raise ValueError("No active station assignments found")

        # All stations share the same revenue model — use first distribution's
        first_distribution = distributions[0]
        revenue_share = first_distribution.revenue_share if hasattr(first_distribution, 'revenue_share') else None

        if not revenue_share:
            raise ValueError("No revenue model configured")

        # Build stations list
        stations = []
        for distribution in distributions:
            stations.append({
                'id': str(distribution.station.id),
                'name': distribution.station.station_name,
                'code': distribution.station.serial_number,
                'address': distribution.station.address,
                'total_slots': distribution.station.total_slots,
                'distribution_id': str(distribution.id),
                'effective_date': distribution.effective_date
            })

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
            'stations': stations,
            'station_count': len(stations),
            'distribution': {
                'distribution_type': first_distribution.distribution_type,
                'is_active': first_distribution.is_active
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
            return f"You receive {revenue_share.partner_percent}% of net revenue from each station"
        else:  # FIXED
            return f"You pay NPR {revenue_share.fixed_amount} monthly to the station owner per station"
