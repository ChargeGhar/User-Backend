"""
Station Analytics Service
Provides analytics data for station performance, utilization, and revenue
"""
from decimal import Decimal
from datetime import timedelta
from django.db.models import Count, Sum, Avg, Q, F, Case, When, FloatField
from django.db.models.functions import TruncWeek
from django.utils import timezone

from api.user.stations.models import Station, StationSlot
from api.user.rentals.models import Rental
from api.user.payments.models import Transaction


class StationAnalyticsService:
    """Service for station analytics operations"""
    
    @staticmethod
    def get_station_analytics():
        """
        Get comprehensive station analytics data
        
        Returns:
            dict: Station analytics including performance, utilization, and revenue
        """
        # Station summary
        total_stations = Station.objects.filter(is_deleted=False).count()
        online_stations = Station.objects.filter(status='ONLINE', is_deleted=False).count()
        offline_stations = Station.objects.filter(status='OFFLINE', is_deleted=False).count()
        maintenance_stations = Station.objects.filter(status='MAINTENANCE', is_deleted=False).count()
        
        # Use actual StationSlot count instead of Station.total_slots field
        # This ensures accuracy when slots haven't been created yet
        total_slots = StationSlot.objects.filter(station__is_deleted=False).count()
        
        occupied_slots = StationSlot.objects.filter(
            status='OCCUPIED',
            station__is_deleted=False
        ).count()
        
        utilization_rate = round((occupied_slots / total_slots * 100), 2) if total_slots > 0 else 0
        
        # Top 10 stations by revenue
        # Note: Transaction has 'related_rental' FK, not reverse 'related_transactions'
        # We need to aggregate revenue from Transaction model filtering by station rentals
        from api.user.payments.models import Transaction
        
        top_stations = Station.objects.filter(
            is_deleted=False
        ).annotate(
            total_rentals=Count('rentals', filter=Q(
                rentals__status__in=['ACTIVE', 'COMPLETED', 'OVERDUE']
            )),
            occupied_slot_count=Count('slots', filter=Q(slots__status='OCCUPIED')),
            avg_duration_seconds=Avg(
                F('rentals__ended_at') - F('rentals__started_at'),
                filter=Q(rentals__status='COMPLETED', rentals__ended_at__isnull=False)
            )
        ).order_by('-total_rentals')[:50]  # Get top 50 by rentals first
        
        # Calculate revenue for each station manually since Transaction -> Rental relationship
        top_stations_with_revenue = []
        for station in top_stations:
            revenue = Transaction.objects.filter(
                related_rental__station=station,
                status='SUCCESS'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if revenue > 0:
                top_stations_with_revenue.append({
                    'station': station,
                    'total_rentals': station.total_rentals,
                    'total_revenue': revenue,
                    'occupied_slot_count': station.occupied_slot_count,
                    'avg_duration_seconds': station.avg_duration_seconds
                })
        
        # Sort by revenue and take top 10
        top_stations_with_revenue.sort(key=lambda x: x['total_revenue'], reverse=True)
        top_stations_list = top_stations_with_revenue[:10]
        
        top_stations_data = []
        revenue_chart_labels = []
        revenue_chart_data = []
        rental_chart_labels = []
        rental_chart_data = []
        
        for station_data in top_stations_list:
            station = station_data['station']
            
            # Get actual slot count for this station
            actual_slot_count = station.slots.count()
            
            # Calculate utilization rate
            utilization = round(
                (station_data['occupied_slot_count'] / actual_slot_count * 100), 2
            ) if actual_slot_count > 0 else 0
            
            # Convert avg duration to minutes
            if station_data['avg_duration_seconds']:
                avg_duration = station_data['avg_duration_seconds'].total_seconds() / 60
            else:
                avg_duration = 0
            
            # Get payment methods for this station
            station_pm = Transaction.objects.filter(
                status='SUCCESS',
                related_rental__station=station,
                related_rental__isnull=False
            ).values('payment_method_type').annotate(count=Count('id'))
            
            payment_methods = {
                'wallet': 0,
                'gateway': 0,
                'points': 0,
                'combination': 0
            }
            
            for pm in station_pm:
                method_key = pm['payment_method_type'].lower()
                if method_key in payment_methods:
                    payment_methods[method_key] = pm['count']
            
            station_item = {
                'station_id': str(station.id),
                'station_name': station.station_name,
                'serial_number': station.serial_number,
                'total_rentals': station_data['total_rentals'],
                'total_revenue': float(station_data['total_revenue']),
                'total_slots': actual_slot_count,
                'occupied_slots': station_data['occupied_slot_count'],
                'utilization_rate': utilization,
                'average_rental_duration': round(avg_duration, 2),
                'status': station.status,
                'address': station.address,
                'payment_methods': payment_methods
            }
            
            top_stations_data.append(station_item)
            
            # Add to charts (top 5 for charts)
            if len(revenue_chart_labels) < 5:
                revenue_chart_labels.append(station.station_name)
                revenue_chart_data.append(float(station_data['total_revenue']))
                rental_chart_labels.append(station.station_name)
                rental_chart_data.append(station_data['total_rentals'])
        
        # Station status distribution
        status_labels = ['Online', 'Offline', 'Maintenance']
        status_values = [online_stations, offline_stations, maintenance_stations]
        
        # Utilization trend - last 4 weeks
        now = timezone.now()
        trend_labels = []
        trend_data = []
        
        for i in range(3, -1, -1):
            week_start = now - timedelta(days=(i + 1) * 7)
            week_end = now - timedelta(days=i * 7)
            
            # Get average utilization for the week
            week_total_slots = StationSlot.objects.filter(
                station__is_deleted=False
            ).count()
            
            # Approximate occupied slots (using rental counts as proxy)
            week_occupied = Rental.objects.filter(
                status='ACTIVE',
                started_at__gte=week_start,
                started_at__lt=week_end
            ).count()
            
            week_utilization = round(
                (week_occupied / week_total_slots * 100), 2
            ) if week_total_slots > 0 else 0
            
            label = f"{week_start.strftime('%b %d')}-{week_end.strftime('%d')}"
            trend_labels.append(label)
            trend_data.append(week_utilization)
        
        return {
            'summary': {
                'total_stations': total_stations,
                'online_stations': online_stations,
                'offline_stations': offline_stations,
                'maintenance_stations': maintenance_stations,
                'total_slots': total_slots,
                'occupied_slots': occupied_slots,
                'utilization_rate': utilization_rate
            },
            'top_10_stations': top_stations_data,
            'station_revenue_chart': {
                'labels': revenue_chart_labels,
                'datasets': [{
                    'label': 'Revenue (NPR)',
                    'data': revenue_chart_data
                }]
            },
            'station_rental_count_chart': {
                'labels': rental_chart_labels,
                'datasets': [{
                    'label': 'Rentals',
                    'data': rental_chart_data
                }]
            },
            'station_status_distribution': {
                'labels': status_labels,
                'values': status_values
            },
            'utilization_trend': {
                'labels': trend_labels,
                'period': 'Last 4 weeks',
                'datasets': [{
                    'label': 'Utilization Rate (%)',
                    'data': trend_data
                }]
            }
        }
