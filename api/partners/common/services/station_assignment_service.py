"""
StationAssignmentService - Common service for station distribution and revenue share management.

Business Rules:
- BR2.3: Vendor can have ONLY ONE station
- BR3.1: One station = one active distribution at a time
- BR3.3: Revenue model options - Fixed OR Percentage
- BR3.4: Non-Revenue vendors have NO revenue model
- BR6.2: CG Vendor gets partner_percent of net revenue
- BR7.4: Franchise Vendor gets partner_percent from Franchise's share
"""

from typing import Dict, Optional
from decimal import Decimal

from api.common.services.base import BaseService, ServiceException
from api.partners.common.repositories import (
    StationDistributionRepository,
    StationRevenueShareRepository,
    PartnerRepository
)


class StationAssignmentService(BaseService):
    """Service for station assignment and revenue share management"""
    
    def assign_station(
        self,
        station_id: str,
        partner_id: str,
        distribution_type: str,
        assigned_by_id: str,
        revenue_config: Optional[Dict] = None,
        notes: Optional[str] = None
    ):
        """
        Assign station to partner with optional revenue configuration.
        
        Args:
            station_id: Station UUID
            partner_id: Partner UUID
            distribution_type: CHARGEGHAR_TO_FRANCHISE, CHARGEGHAR_TO_VENDOR, FRANCHISE_TO_VENDOR
            assigned_by_id: User UUID who assigned
            revenue_config: Optional dict with revenue_model, partner_percent, fixed_amount
            notes: Optional notes
            
        Returns:
            Dict with distribution and revenue_share (if applicable)
            
        Raises:
            ServiceException: If validation fails
        """
        # Validate station exists
        from api.user.stations.models import Station
        try:
            station = Station.objects.get(id=station_id)
        except Station.DoesNotExist:
            raise ServiceException("Station not found", code="station_not_found")
        
        # Validate partner exists
        partner = PartnerRepository.get_by_id(partner_id)
        if not partner:
            raise ServiceException("Partner not found", code="partner_not_found")
        
        # BR2.3: Check if vendor already has a station
        if partner.partner_type == 'VENDOR':
            existing = StationDistributionRepository.get_active_by_partner(partner_id).filter(
                is_active=True
            ).first()
            if existing:
                raise ServiceException(
                    "Vendor already has an assigned station",
                    code="vendor_already_has_station"
                )
        
        # BR3.1: Check if station already assigned
        existing_dist = StationDistributionRepository.get_active_by_station(station_id)
        if existing_dist:
            raise ServiceException(
                f"Station already assigned to partner {existing_dist.partner.code}",
                code="station_already_assigned"
            )
        
        # Validate distribution type
        valid_types = ['CHARGEGHAR_TO_FRANCHISE', 'CHARGEGHAR_TO_VENDOR', 'FRANCHISE_TO_VENDOR']
        if distribution_type not in valid_types:
            raise ServiceException(
                f"Invalid distribution type. Must be one of: {', '.join(valid_types)}",
                code="invalid_distribution_type"
            )
        
        # Validate revenue config for REVENUE vendors
        if partner.partner_type == 'VENDOR' and partner.vendor_type == 'REVENUE':
            if not revenue_config:
                raise ServiceException(
                    "Revenue configuration required for REVENUE vendor",
                    code="revenue_config_required"
                )
            self._validate_revenue_config(revenue_config)
        
        # BR3.4: Non-Revenue vendors should NOT have revenue config
        if partner.partner_type == 'VENDOR' and partner.vendor_type == 'NON_REVENUE':
            if revenue_config:
                raise ServiceException(
                    "Non-Revenue vendors cannot have revenue configuration",
                    code="non_revenue_cannot_have_config"
                )
        
        # Create distribution
        distribution = StationDistributionRepository.create(
            station_id=station_id,
            partner_id=partner_id,
            distribution_type=distribution_type,
            assigned_by_id=assigned_by_id,
            notes=notes
        )
        
        self.log_info(
            f"Station {station.name} assigned to partner {partner.code} "
            f"(type: {distribution_type})"
        )
        
        # Create revenue share if applicable
        revenue_share = None
        if revenue_config:
            revenue_share = self._create_revenue_share(
                distribution_id=str(distribution.id),
                revenue_config=revenue_config
            )
        
        return {
            'distribution': distribution,
            'revenue_share': revenue_share
        }
    
    def update_revenue_share(
        self,
        distribution_id: str,
        revenue_config: Dict
    ):
        """
        Update revenue share configuration for existing distribution.
        
        Args:
            distribution_id: StationDistribution UUID
            revenue_config: Dict with revenue_model, partner_percent, fixed_amount
            
        Returns:
            Updated StationRevenueShare object
            
        Raises:
            ServiceException: If validation fails
        """
        # Get distribution
        distribution = StationDistributionRepository.get_by_id(distribution_id)
        if not distribution:
            raise ServiceException(
                "Distribution not found",
                code="distribution_not_found"
            )
        
        # Validate partner is REVENUE vendor
        partner = distribution.partner
        if partner.partner_type != 'VENDOR' or partner.vendor_type != 'REVENUE':
            raise ServiceException(
                "Revenue share can only be updated for REVENUE vendors",
                code="not_revenue_vendor"
            )
        
        # Validate revenue config
        self._validate_revenue_config(revenue_config)
        
        # Get existing revenue share
        revenue_share = StationRevenueShareRepository.get_by_distribution(distribution_id)
        
        if revenue_share:
            # Update existing
            revenue_share = StationRevenueShareRepository.update(
                str(revenue_share.id),
                revenue_model=revenue_config['revenue_model'],
                partner_percent=revenue_config.get('partner_percent'),
                fixed_amount=revenue_config.get('fixed_amount')
            )
            self.log_info(f"Updated revenue share for distribution {distribution_id}")
        else:
            # Create new
            revenue_share = self._create_revenue_share(distribution_id, revenue_config)
            self.log_info(f"Created revenue share for distribution {distribution_id}")
        
        return revenue_share
    
    def deactivate_distribution(
        self,
        distribution_id: str,
        reason: Optional[str] = None
    ):
        """
        Deactivate station distribution.
        
        Args:
            distribution_id: StationDistribution UUID
            reason: Optional reason for deactivation
            
        Returns:
            Updated StationDistribution object
            
        Raises:
            ServiceException: If distribution not found
        """
        distribution = StationDistributionRepository.get_by_id(distribution_id)
        if not distribution:
            raise ServiceException(
                "Distribution not found",
                code="distribution_not_found"
            )
        
        if not distribution.is_active:
            raise ServiceException(
                "Distribution already inactive",
                code="already_inactive"
            )
        
        # Deactivate
        from django.utils import timezone
        distribution = StationDistributionRepository.update(
            distribution_id,
            is_active=False,
            expiry_date=timezone.now().date(),
            notes=f"{distribution.notes or ''}\nDeactivated: {reason or 'No reason provided'}"
        )
        
        self.log_info(
            f"Deactivated distribution {distribution_id} "
            f"(station: {distribution.station.name}, partner: {distribution.partner.code})"
        )
        
        return distribution
    
    def get_station_assignment(self, station_id: str) -> Optional[Dict]:
        """
        Get current active assignment for station.
        
        Args:
            station_id: Station UUID
            
        Returns:
            Dict with distribution and revenue_share, or None if not assigned
        """
        distribution = StationDistributionRepository.get_active_by_station(station_id)
        if not distribution:
            return None
        
        revenue_share = None
        if distribution.partner.partner_type == 'VENDOR' and distribution.partner.vendor_type == 'REVENUE':
            revenue_share = StationRevenueShareRepository.get_by_distribution(str(distribution.id))
        
        return {
            'distribution': distribution,
            'revenue_share': revenue_share
        }
    
    def get_partner_assignment(self, partner_id: str) -> Optional[Dict]:
        """
        Get current active assignment for partner.
        
        Args:
            partner_id: Partner UUID
            
        Returns:
            Dict with distribution and revenue_share, or None if not assigned
        """
        distribution = StationDistributionRepository.get_active_by_partner(partner_id).filter(
            is_active=True
        ).select_related('station', 'partner').first()
        
        if not distribution:
            return None
        
        revenue_share = None
        if distribution.partner.partner_type == 'VENDOR' and distribution.partner.vendor_type == 'REVENUE':
            revenue_share = StationRevenueShareRepository.get_by_distribution(str(distribution.id))
        
        return {
            'distribution': distribution,
            'revenue_share': revenue_share
        }
    
    # Private helper methods
    
    def _validate_revenue_config(self, config: Dict):
        """Validate revenue configuration"""
        if 'revenue_model' not in config:
            raise ServiceException(
                "revenue_model is required",
                code="revenue_model_required"
            )
        
        revenue_model = config['revenue_model']
        
        if revenue_model not in ['PERCENTAGE', 'FIXED']:
            raise ServiceException(
                "revenue_model must be PERCENTAGE or FIXED",
                code="invalid_revenue_model"
            )
        
        # BR3.3: Validate percentage model
        if revenue_model == 'PERCENTAGE':
            if not config.get('partner_percent'):
                raise ServiceException(
                    "partner_percent required for PERCENTAGE model",
                    code="partner_percent_required"
                )
            
            partner_percent = Decimal(str(config['partner_percent']))
            if partner_percent <= 0 or partner_percent > 100:
                raise ServiceException(
                    "partner_percent must be between 0 and 100",
                    code="invalid_partner_percent"
                )
        
        # BR3.3: Validate fixed model
        if revenue_model == 'FIXED':
            if not config.get('fixed_amount'):
                raise ServiceException(
                    "fixed_amount required for FIXED model",
                    code="fixed_amount_required"
                )
            
            fixed_amount = Decimal(str(config['fixed_amount']))
            if fixed_amount <= 0:
                raise ServiceException(
                    "fixed_amount must be greater than 0",
                    code="invalid_fixed_amount"
                )
    
    def _create_revenue_share(self, distribution_id: str, config: Dict):
        """Create revenue share record"""
        return StationRevenueShareRepository.create(
            distribution_id=distribution_id,
            revenue_model=config['revenue_model'],
            partner_percent=config.get('partner_percent'),
            fixed_amount=config.get('fixed_amount')
        )
