"""
AdDistribution Repository
==========================
Data access layer for AdDistribution model.
"""
from typing import Optional, List
from django.db.models import QuerySet
from api.user.advertisements.models import AdDistribution


class AdDistributionRepository:
    """Repository for AdDistribution data operations"""
    
    @staticmethod
    def get_by_id(distribution_id: str) -> Optional[AdDistribution]:
        """Get ad distribution by ID"""
        try:
            return AdDistribution.objects.select_related(
                'ad_content__ad_request',
                'station'
            ).get(id=distribution_id)
        except AdDistribution.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_ad_content(ad_content_id: str) -> List[AdDistribution]:
        """Get all distributions for an ad content"""
        return list(AdDistribution.objects.filter(
            ad_content_id=ad_content_id
        ).select_related('station').order_by('-created_at'))
    
    @staticmethod
    def get_by_station(station_id: str) -> List[AdDistribution]:
        """Get all distributions for a station"""
        return list(AdDistribution.objects.filter(
            station_id=station_id
        ).select_related(
            'ad_content__ad_request',
            'ad_content__media_upload'
        ).order_by('-created_at'))
    
    @staticmethod
    def get_active_by_station(station_id: str) -> List[AdDistribution]:
        """Get active ad distributions for a station (where ad is RUNNING)"""
        return list(AdDistribution.objects.filter(
            station_id=station_id,
            ad_content__ad_request__status='RUNNING',
            ad_content__is_active=True
        ).select_related(
            'ad_content__ad_request',
            'ad_content__media_upload'
        ).order_by('ad_content__display_order', '-created_at'))
    
    @staticmethod
    def create(ad_content, station, **kwargs) -> AdDistribution:
        """Create new ad distribution"""
        return AdDistribution.objects.create(
            ad_content=ad_content,
            station=station,
            **kwargs
        )
    
    @staticmethod
    def bulk_create(distributions: List[AdDistribution]) -> List[AdDistribution]:
        """Bulk create ad distributions"""
        return AdDistribution.objects.bulk_create(distributions)
    
    @staticmethod
    def delete_by_ad_content(ad_content_id: str) -> int:
        """Delete all distributions for an ad content"""
        count, _ = AdDistribution.objects.filter(
            ad_content_id=ad_content_id
        ).delete()
        return count
    
    @staticmethod
    def delete_by_station(ad_content_id: str, station_id: str) -> int:
        """Delete specific distribution"""
        count, _ = AdDistribution.objects.filter(
            ad_content_id=ad_content_id,
            station_id=station_id
        ).delete()
        return count
    
    @staticmethod
    def exists(ad_content_id: str, station_id: str) -> bool:
        """Check if distribution exists"""
        return AdDistribution.objects.filter(
            ad_content_id=ad_content_id,
            station_id=station_id
        ).exists()
    
    @staticmethod
    def count_by_ad_content(ad_content_id: str) -> int:
        """Count distributions for an ad content"""
        return AdDistribution.objects.filter(ad_content_id=ad_content_id).count()
    
    @staticmethod
    def count_by_station(station_id: str) -> int:
        """Count distributions for a station"""
        return AdDistribution.objects.filter(station_id=station_id).count()
    
    @staticmethod
    def get_stations_for_ad_content(ad_content_id: str) -> List:
        """Get list of stations for an ad content"""
        distributions = AdDistribution.objects.filter(
            ad_content_id=ad_content_id
        ).select_related('station')
        return [dist.station for dist in distributions]
