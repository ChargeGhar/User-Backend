"""
Partner Station Service (Common for both Franchise and Vendor)

Service layer for partner station operations.
"""

from decimal import Decimal
from datetime import date
from typing import Dict

from django.db.models import Sum, Count, Q
from django.utils import timezone
from api.common.services.base import BaseService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.partners.common.models import Partner, StationDistribution


class PartnerStationService(BaseService):
    """Service for partner station operations (both Franchise and Vendor)"""
    
    def get_stations_list(self, partner: Partner, filters: Dict) -> Dict:
        """
        Get paginated list of partner's own stations.
        
        Args:
            partner: Partner object (FRANCHISE or VENDOR)
            filters: Dict with page, page_size, status, search, has_vendor
            
        Returns:
            Dict with results, count, page, page_size, total_pages
            
        Business Rules:
        - BR10.2: Only own stations
        - BR12.2: Only own revenue data
        - BR2.3: Vendor has only ONE station
        """
        # Determine distribution type based on partner type
        if partner.is_franchise:
            dist_type = StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE
        elif partner.is_vendor and partner.parent is None:
            dist_type = StationDistribution.DistributionType.CHARGEGHAR_TO_VENDOR
        elif partner.is_vendor and partner.parent is not None:
            dist_type = StationDistribution.DistributionType.FRANCHISE_TO_VENDOR
        else:
            raise ValueError("Invalid partner type")
        
        # Get base queryset
        from api.user.stations.models import Station
        
        queryset = Station.objects.filter(
            partner_distributions__partner_id=partner.id,
            partner_distributions__distribution_type=dist_type,
            partner_distributions__is_active=True,
            is_deleted=False
        ).select_related().prefetch_related(
            'slots',
            'amenity_mappings__amenity'
        ).distinct()
        
        # Apply filters
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('search'):
            search = filters['search']
            queryset = queryset.filter(
                Q(station_name__icontains=search) |
                Q(serial_number__icontains=search) |
                Q(address__icontains=search)
            )
        
        # has_vendor filter only applies to franchises
        if partner.is_franchise and filters.get('has_vendor') is not None:
            has_vendor = filters['has_vendor'] == 'true' or filters['has_vendor'] is True
            if has_vendor:
                queryset = queryset.filter(
                    partner_distributions__distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR,
                    partner_distributions__is_active=True
                )
            else:
                vendor_station_ids = StationDistribution.objects.filter(
                    distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR,
                    is_active=True
                ).values_list('station_id', flat=True)
                queryset = queryset.exclude(id__in=vendor_station_ids)
        
        # Paginate
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        
        paginated = paginate_queryset(queryset, page, page_size)
        
        # Build results with stats
        results = []
        station_ids = [str(s.id) for s in paginated['results']]
        
        # Get revenue stats for all stations in bulk
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        revenue_today = self._get_revenue_stats_bulk(partner.id, station_ids, today, today)
        revenue_month = self._get_revenue_stats_bulk(partner.id, station_ids, month_start, today)
        
        # Get powerbank stats in bulk
        powerbank_stats = self._get_powerbank_stats_bulk(station_ids)
        
        for station in paginated['results']:
            station_id = str(station.id)
            
            # Get distribution info
            own_dist = StationDistribution.objects.filter(
                station_id=station.id,
                partner_id=partner.id,
                distribution_type=dist_type,
                is_active=True
            ).first()
            
            # Get assigned partner info (vendor for franchise, or franchise for vendor)
            assigned_partner = None
            if partner.is_franchise:
                # Check if assigned to vendor
                vendor_dist = StationDistribution.objects.filter(
                    station_id=station.id,
                    distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR,
                    is_active=True
                ).select_related('partner').first()
                if vendor_dist:
                    assigned_partner = vendor_dist.partner
            
            # Get amenities
            amenities = [
                mapping.amenity.name 
                for mapping in station.amenity_mappings.filter(
                    amenity__is_active=True,
                    is_available=True
                )
            ]
            
            # Slot counts
            available_slots = station.slots.filter(status='AVAILABLE').count()
            occupied_slots = station.slots.filter(status='OCCUPIED').count()
            
            results.append({
                'id': station.id,
                'station_name': station.station_name,
                'serial_number': station.serial_number,
                'imei': station.imei,
                'latitude': station.latitude,
                'longitude': station.longitude,
                'address': station.address,
                'landmark': station.landmark,
                'total_slots': station.total_slots,
                'status': station.status,
                'is_maintenance': station.is_maintenance,
                'last_heartbeat': station.last_heartbeat,
                'created_at': station.created_at,
                'updated_at': station.updated_at,
                'amenities': amenities,
                'available_slots': available_slots,
                'occupied_slots': occupied_slots,
                'total_powerbanks': powerbank_stats.get(station_id, {}).get('total', 0),
                'available_powerbanks': powerbank_stats.get(station_id, {}).get('available', 0),
                'distribution': {
                    'id': own_dist.id,
                    'distribution_type': own_dist.distribution_type,
                    'effective_date': own_dist.effective_date,
                    'is_active': own_dist.is_active,
                } if own_dist else None,
                'assigned_partner': {
                    'id': assigned_partner.id,
                    'code': assigned_partner.code,
                    'business_name': assigned_partner.business_name,
                    'partner_type': assigned_partner.partner_type,
                    'vendor_type': assigned_partner.vendor_type if assigned_partner.is_vendor else None,
                    'status': assigned_partner.status,
                } if assigned_partner else None,
                'revenue_stats': {
                    'today_transactions': revenue_today.get(station_id, {}).get('transactions', 0),
                    'today_revenue': revenue_today.get(station_id, {}).get('revenue', Decimal('0')),
                    'this_month_transactions': revenue_month.get(station_id, {}).get('transactions', 0),
                    'this_month_revenue': revenue_month.get(station_id, {}).get('revenue', Decimal('0')),
                }
            })
        
        return {
            'results': results,
            'pagination': paginated['pagination']
        }
    
    def get_station_detail(self, partner: Partner, station_id: str) -> Dict:
        """
        Get detailed station info with slots, powerbanks, media.
        
        Args:
            partner: Partner object (FRANCHISE or VENDOR)
            station_id: Station UUID
            
        Returns:
            Dict with complete station details
            
        Business Rules:
        - BR10.2: Only own stations
        - BR12.2: Only own data
        """
        from api.user.stations.models import Station, PowerBank
        
        # Determine distribution type
        if partner.is_franchise:
            dist_type = StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE
        elif partner.is_vendor and partner.parent is None:
            dist_type = StationDistribution.DistributionType.CHARGEGHAR_TO_VENDOR
        elif partner.is_vendor and partner.parent is not None:
            dist_type = StationDistribution.DistributionType.FRANCHISE_TO_VENDOR
        else:
            raise ValueError("Invalid partner type")
        
        # Verify ownership
        station = Station.objects.filter(
            id=station_id,
            partner_distributions__partner_id=partner.id,
            partner_distributions__distribution_type=dist_type,
            partner_distributions__is_active=True,
            is_deleted=False
        ).prefetch_related(
            'slots',
            'amenity_mappings__amenity',
            'media__media_upload'
        ).first()
        
        if not station:
            raise ServiceException(
                detail="Station not found or access denied",
                code="STATION_NOT_FOUND"
            )
        
        # Get distribution
        own_dist = StationDistribution.objects.filter(
            station_id=station.id,
            partner_id=partner.id,
            distribution_type=dist_type,
            is_active=True
        ).first()
        
        # Get assigned partner (vendor for franchise, franchise for vendor)
        assigned_partner = None
        if partner.is_franchise:
            vendor_dist = StationDistribution.objects.filter(
                station_id=station.id,
                distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR,
                is_active=True
            ).select_related('partner').first()
            if vendor_dist:
                assigned_partner = vendor_dist.partner
        
        # Get amenities
        amenities = [{
            'id': m.amenity.id,
            'name': m.amenity.name,
            'icon': m.amenity.icon,
            'description': m.amenity.description,
            'is_active': m.amenity.is_active,
            'is_available': m.is_available
        } for m in station.amenity_mappings.filter(amenity__is_active=True)]
        
        # Get media
        media = [{
            'id': sm.id,
            'media_upload_id': sm.media_upload.id,
            'media_type': sm.media_type,
            'title': sm.title,
            'description': sm.description,
            'is_primary': sm.is_primary,
            'file_url': sm.media_upload.file_url,
            'thumbnail_url': sm.media_upload.file_url,
            'created_at': sm.created_at
        } for sm in station.media.select_related('media_upload').order_by('-is_primary', 'created_at')]
        
        # Get slots with powerbanks
        slots = []
        for slot in station.slots.order_by('slot_number'):
            powerbank = PowerBank.objects.filter(current_slot=slot).first()
            slots.append({
                'id': slot.id,
                'slot_number': slot.slot_number,
                'status': slot.status,
                'battery_level': slot.battery_level,
                'last_updated': slot.last_updated,
                'powerbank': {
                    'id': powerbank.id,
                    'serial_number': powerbank.serial_number,
                    'model': powerbank.model,
                    'capacity_mah': powerbank.capacity_mah,
                    'battery_level': powerbank.battery_level,
                    'status': powerbank.status
                } if powerbank else None,
                'current_rental_id': str(slot.current_rental.id) if slot.current_rental else None
            })
        
        # Get all powerbanks at station
        powerbanks = [{
            'id': pb.id,
            'serial_number': pb.serial_number,
            'model': pb.model,
            'capacity_mah': pb.capacity_mah,
            'status': pb.status,
            'battery_level': pb.battery_level,
            'slot_number': pb.current_slot.slot_number if pb.current_slot else None,
            'last_updated': pb.last_updated
        } for pb in PowerBank.objects.filter(current_station=station).select_related('current_slot')]
        
        return {
            'id': station.id,
            'station_name': station.station_name,
            'serial_number': station.serial_number,
            'imei': station.imei,
            'latitude': station.latitude,
            'longitude': station.longitude,
            'address': station.address,
            'landmark': station.landmark,
            'description': station.description,
            'total_slots': station.total_slots,
            'status': station.status,
            'is_maintenance': station.is_maintenance,
            'is_deleted': station.is_deleted,
            'hardware_info': station.hardware_info,
            'last_heartbeat': station.last_heartbeat,
            'opening_time': station.opening_time,
            'closing_time': station.closing_time,
            'created_at': station.created_at,
            'updated_at': station.updated_at,
            'amenities': amenities,
            'media': media,
            'slots': slots,
            'powerbanks': powerbanks,
            'distribution': {
                'id': own_dist.id,
                'distribution_type': own_dist.distribution_type,
                'effective_date': own_dist.effective_date,
                'is_active': own_dist.is_active,
            } if own_dist else None,
            'assigned_partner': {
                'id': assigned_partner.id,
                'code': assigned_partner.code,
                'business_name': assigned_partner.business_name,
                'partner_type': assigned_partner.partner_type,
                'vendor_type': assigned_partner.vendor_type if assigned_partner.is_vendor else None,
                'status': assigned_partner.status,
            } if assigned_partner else None
        }
    
    def _get_revenue_stats_bulk(self, partner_id: str, station_ids: list, start_date: date, end_date: date) -> Dict:
        """Get revenue stats for multiple stations"""
        from api.partners.common.models import RevenueDistribution
        
        # Get revenue based on partner type
        partner = Partner.objects.get(id=partner_id)
        
        if partner.is_franchise:
            filter_field = 'franchise_id'
        elif partner.is_vendor:
            filter_field = 'vendor_id'
        else:
            return {}
        
        stats = RevenueDistribution.objects.filter(
            **{filter_field: partner_id},
            station_id__in=station_ids,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_reversal=False
        ).values('station_id').annotate(
            transactions=Count('id'),
            revenue=Sum('gross_amount')
        )
        
        return {
            str(s['station_id']): {
                'transactions': s['transactions'],
                'revenue': s['revenue'] or Decimal('0')
            }
            for s in stats
        }
    
    def _get_powerbank_stats_bulk(self, station_ids: list) -> Dict:
        """Get powerbank stats for multiple stations"""
        from api.user.stations.models import PowerBank
        
        stats = PowerBank.objects.filter(
            current_station_id__in=station_ids
        ).values('current_station_id').annotate(
            total=Count('id'),
            available=Count('id', filter=Q(status='AVAILABLE'))
        )
        
        return {
            str(s['current_station_id']): {
                'total': s['total'],
                'available': s['available']
            }
            for s in stats
        }
