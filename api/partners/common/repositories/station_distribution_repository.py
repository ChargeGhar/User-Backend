from typing import Optional, List
from django.db.models import QuerySet
from django.utils import timezone

from api.partners.common.models import StationDistribution, Partner


class StationDistributionRepository:
    """
    Repository for StationDistribution model database operations.
    """
    
    @staticmethod
    def get_by_id(distribution_id: str) -> Optional[StationDistribution]:
        """Get distribution by ID"""
        try:
            return StationDistribution.objects.select_related(
                'station', 'partner', 'partner__parent', 'assigned_by'
            ).get(id=distribution_id)
        except StationDistribution.DoesNotExist:
            return None
    
    @staticmethod
    def get_active_by_station(station_id: str) -> QuerySet:
        """Get all active distributions for a station"""
        return StationDistribution.objects.filter(
            station_id=station_id,
            is_active=True
        ).select_related('partner', 'partner__parent')
    
    @staticmethod
    def get_active_by_partner(partner_id: str) -> QuerySet:
        """Get all active distributions for a partner"""
        return StationDistribution.objects.filter(
            partner_id=partner_id,
            is_active=True
        ).select_related('station')
    
    @staticmethod
    def get_station_operator(station_id: str) -> Optional[Partner]:
        """
        Get the current operator of a station.
        
        Returns Partner or None if no operator assigned.
        
        Logic:
        1. Check for active FRANCHISE_TO_VENDOR first (vendor operates franchise station)
        2. Check for active CHARGEGHAR_TO_VENDOR (vendor operates CG station)
        3. Check for active CHARGEGHAR_TO_FRANCHISE (franchise operates own station)
        4. None = ChargeGhar operates directly
        """
        # Check for vendor operator first
        vendor_dist = StationDistribution.objects.filter(
            station_id=station_id,
            is_active=True,
            distribution_type__in=[
                StationDistribution.DistributionType.CHARGEGHAR_TO_VENDOR,
                StationDistribution.DistributionType.FRANCHISE_TO_VENDOR
            ]
        ).select_related('partner').first()
        
        if vendor_dist:
            return vendor_dist.partner
        
        # Check for franchise operator
        franchise_dist = StationDistribution.objects.filter(
            station_id=station_id,
            is_active=True,
            distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE
        ).select_related('partner').first()
        
        if franchise_dist:
            return franchise_dist.partner
        
        return None
    
    @staticmethod
    def get_station_franchise(station_id: str) -> Optional[Partner]:
        """
        Get the franchise that owns a station (if any).
        
        Returns Partner (franchise) or None.
        """
        franchise_dist = StationDistribution.objects.filter(
            station_id=station_id,
            is_active=True,
            distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE
        ).select_related('partner').first()
        
        return franchise_dist.partner if franchise_dist else None
    
    @staticmethod
    def get_station_vendor(station_id: str) -> Optional[Partner]:
        """
        Get the vendor operating a station (if any).
        
        Returns Partner (vendor) or None.
        """
        vendor_dist = StationDistribution.objects.filter(
            station_id=station_id,
            is_active=True,
            distribution_type__in=[
                StationDistribution.DistributionType.CHARGEGHAR_TO_VENDOR,
                StationDistribution.DistributionType.FRANCHISE_TO_VENDOR
            ]
        ).select_related('partner').first()
        
        return vendor_dist.partner if vendor_dist else None
    
    @staticmethod
    def vendor_has_station(partner_id: str) -> bool:
        """Check if vendor already has an active station assignment"""
        return StationDistribution.objects.filter(
            partner_id=partner_id,
            is_active=True,
            distribution_type__in=[
                StationDistribution.DistributionType.CHARGEGHAR_TO_VENDOR,
                StationDistribution.DistributionType.FRANCHISE_TO_VENDOR
            ]
        ).exists()
    
    @staticmethod
    def station_has_operator(station_id: str) -> bool:
        """Check if station already has an active operator"""
        return StationDistribution.objects.filter(
            station_id=station_id,
            is_active=True,
            distribution_type__in=[
                StationDistribution.DistributionType.CHARGEGHAR_TO_VENDOR,
                StationDistribution.DistributionType.FRANCHISE_TO_VENDOR
            ]
        ).exists()
    
    @staticmethod
    def create(
        station_id: str,
        partner_id: str,
        distribution_type: str,
        assigned_by_id: int,
        notes: Optional[str] = None
    ) -> StationDistribution:
        """Create a new station distribution"""
        return StationDistribution.objects.create(
            station_id=station_id,
            partner_id=partner_id,
            distribution_type=distribution_type,
            assigned_by_id=assigned_by_id,
            notes=notes
        )
    
    @staticmethod
    def deactivate(distribution_id: str) -> Optional[StationDistribution]:
        """Deactivate a station distribution"""
        try:
            dist = StationDistribution.objects.get(id=distribution_id)
            dist.is_active = False
            dist.expiry_date = timezone.now().date()
            dist.save(update_fields=['is_active', 'expiry_date', 'updated_at'])
            return dist
        except StationDistribution.DoesNotExist:
            return None
    
    @staticmethod
    def deactivate_by_station_and_partner(station_id: str, partner_id: str) -> int:
        """Deactivate all distributions for a station-partner pair"""
        return StationDistribution.objects.filter(
            station_id=station_id,
            partner_id=partner_id,
            is_active=True
        ).update(
            is_active=False,
            expiry_date=timezone.now().date()
        )
    
    @staticmethod
    def get_franchise_stations(franchise_id: str) -> QuerySet:
        """Get all stations owned by a franchise"""
        return StationDistribution.objects.filter(
            partner_id=franchise_id,
            is_active=True,
            distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE
        ).select_related('station')
    
    @staticmethod
    def get_franchise_unassigned_stations(franchise_id: str) -> QuerySet:
        """
        Get franchise stations that don't have a vendor assigned.
        These are stations the franchise can assign to vendors.
        """
        # Get all station IDs that have active vendor assignments
        assigned_station_ids = StationDistribution.objects.filter(
            is_active=True,
            distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR
        ).values_list('station_id', flat=True)
        
        # Get franchise stations not in the assigned list
        return StationDistribution.objects.filter(
            partner_id=franchise_id,
            is_active=True,
            distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE
        ).exclude(
            station_id__in=assigned_station_ids
        ).select_related('station')
    
    @staticmethod
    def get_unassigned_stations() -> QuerySet:
        """
        Get all stations that don't have any partner assignment.
        These are ChargeGhar-operated stations available for assignment.
        """
        from api.user.stations.models import Station
        
        # Get all station IDs that have active distributions
        assigned_station_ids = StationDistribution.objects.filter(
            is_active=True
        ).values_list('station_id', flat=True)
        
        return Station.objects.exclude(id__in=assigned_station_ids)
    
    @staticmethod
    def filter_distributions(
        station_id: Optional[str] = None,
        partner_id: Optional[str] = None,
        distribution_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> QuerySet:
        """Filter distributions with various criteria"""
        queryset = StationDistribution.objects.select_related(
            'station', 'partner', 'partner__parent'
        )
        
        if station_id:
            queryset = queryset.filter(station_id=station_id)
        
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        
        if distribution_type:
            queryset = queryset.filter(distribution_type=distribution_type)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        return queryset.order_by('-created_at')
