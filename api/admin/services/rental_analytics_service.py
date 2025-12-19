"""
PowerBank Rental Analytics Service
"""
from __future__ import annotations
from typing import Dict, Any
from django.db.models import Count, Q
from api.common.services.base import BaseService
from api.rentals.models import Rental
from api.stations.models import PowerBank


class RentalAnalyticsService(BaseService):
    """Service for powerbank rental analytics"""
    
    def get_powerbank_rental_analytics(self) -> Dict[str, Any]:
        """Get PowerBank rental analytics for chart visualization"""
        try:
            # Summary statistics
            total_powerbanks = PowerBank.objects.count()
            total_rentals = Rental.objects.exclude(power_bank__isnull=True).count()
            active_rentals_count = Rental.objects.filter(
                status__in=['ACTIVE', 'OVERDUE']
            ).count()
            
            # Calculate average cycles per powerbank
            avg_cycles = total_rentals / total_powerbanks if total_powerbanks > 0 else 0
            
            # Rental status distribution - single query
            status_counts = Rental.objects.aggregate(
                completed=Count('id', filter=Q(status='COMPLETED')),
                active=Count('id', filter=Q(status='ACTIVE')),
                overdue=Count('id', filter=Q(status='OVERDUE')),
                cancelled=Count('id', filter=Q(status='CANCELLED'))
            )
            
            # Completion stats (only COMPLETED rentals)
            completion_stats = Rental.objects.filter(
                status='COMPLETED'
            ).aggregate(
                on_time=Count('id', filter=Q(is_returned_on_time=True)),
                late=Count('id', filter=Q(is_returned_on_time=False))
            )
            
            on_time_count = completion_stats['on_time'] or 0
            late_count = completion_stats['late'] or 0
            total_completed = on_time_count + late_count
            on_time_percentage = (on_time_count / total_completed * 100) if total_completed > 0 else 0
            
            # PowerBank rental cycles (top 10)
            powerbank_cycles = Rental.objects.filter(
                power_bank__isnull=False
            ).values(
                'power_bank__serial_number',
                'power_bank__status',
                'power_bank__current_station__station_name'
            ).annotate(
                total_cycles=Count('id')
            ).order_by('-total_cycles')[:10]
            
            # Format powerbank cycles for chart
            pb_cycles_labels = []
            pb_cycles_data = []
            pb_details = []
            
            for pb in powerbank_cycles:
                serial = pb['power_bank__serial_number']
                pb_cycles_labels.append(serial)
                pb_cycles_data.append(pb['total_cycles'])
                pb_details.append({
                    'serial_number': serial,
                    'status': pb['power_bank__status'],
                    'total_cycles': pb['total_cycles'],
                    'current_station': pb['power_bank__current_station__station_name'] or 'N/A'
                })
            
            # Find most and least rented powerbanks
            most_rented = pb_details[0]['serial_number'] if pb_details else 'N/A'
            least_rented = pb_details[-1]['serial_number'] if pb_details else 'N/A'
            
            return {
                'summary': {
                    'total_powerbanks': total_powerbanks,
                    'total_rentals': total_rentals,
                    'active_rentals': active_rentals_count,
                    'average_cycles_per_powerbank': round(avg_cycles, 2)
                },
                'rental_status_chart': {
                    'labels': ['Completed', 'Active', 'Overdue', 'Cancelled'],
                    'values': [
                        status_counts['completed'],
                        status_counts['active'],
                        status_counts['overdue'],
                        status_counts['cancelled']
                    ]
                },
                'powerbank_cycles_chart': {
                    'labels': pb_cycles_labels,
                    'datasets': [{
                        'label': 'Total Rentals',
                        'data': pb_cycles_data
                    }]
                },
                'completion_chart': {
                    'labels': ['On Time', 'Late'],
                    'values': [on_time_count, late_count],
                    'percentages': [round(on_time_percentage, 2), round(100 - on_time_percentage, 2)]
                },
                'powerbank_details': pb_details,
                'stats': {
                    'rented': status_counts['active'] + status_counts['overdue'],
                    'completed': status_counts['completed'],
                    'cancelled': status_counts['cancelled'],
                    'due': status_counts['overdue'],
                    'incomplete': status_counts['active'],
                    'on_time_returns': on_time_count,
                    'late_returns': late_count,
                    'on_time_percentage': round(on_time_percentage, 2),
                    'most_rented_powerbank': most_rented,
                    'least_rented_powerbank': least_rented
                }
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get powerbank rental analytics")
