"""
Internal Ad Distribution Service
=================================
Service for fetching active advertisements for hardware stations.
"""
from __future__ import annotations

from datetime import date
from typing import List, Dict, Any

from api.common.services.base import BaseService, ServiceException
from api.user.advertisements.models import AdDistribution
from api.user.stations.models import Station


class AdDistributionService(BaseService):
    """Service for device-facing ad distribution queries"""
    
    def get_active_ads_for_station(self, station_serial: str) -> List[Dict[str, Any]]:
        """
        Get active advertisements for a station by its IMEI/serial.
        
        Business Rules:
        1. Station must exist and not be deleted
        2. Only RUNNING ads within start_date..end_date range
        3. Only active AdContent records
        4. Ordered by display_order (priority)
        
        Args:
            station_serial: Station IMEI or serial number
            
        Returns:
            List of ad dicts matching manufacturer API contract
            
        Raises:
            ServiceException: If station not found
        """
        # Validate station exists
        try:
            station = Station.objects.get(imei=station_serial, is_deleted=False)
        except Station.DoesNotExist:
            raise ServiceException(
                detail="Station not found",
                code="station_not_found",
                status_code=404,
            )
        
        today = date.today()
        
        # Query active distributions with all related data
        distributions = (
            AdDistribution.objects.filter(
                station=station,
                ad_content__is_active=True,
                ad_content__ad_request__status="RUNNING",
                ad_content__ad_request__start_date__lte=today,
                ad_content__ad_request__end_date__gte=today,
            )
            .select_related(
                "ad_content",
                "ad_content__ad_request",
                "ad_content__media_upload",
                "station",
            )
            .order_by("ad_content__display_order", "-created_at")
        )
        
        # Build response data matching manufacturer contract
        ads = []
        for dist in distributions:
            content = dist.ad_content
            ad_request = content.ad_request
            
            ads.append({
                "id": str(content.id),
                "title": ad_request.title or "Untitled",
                "file_type": 1 if content.content_type == "VIDEO" else 0,
                "url_small": content.url_small or "",
                "url_large": content.url_large or "",
                "url3": "",  # reserved
                "forward": content.redirect_url or "",
                "play_time": content.duration_seconds,
                "weight": content.display_order,
                "screen_brightness": 80,  # default; configurable per-content later
                "guuid": str(content.id),
                "position": "ALL",
            })
        
        return ads
