"""
RentalAnalyticsService - Analytics & Statistics Service
============================================================

Provides comprehensive analytics and statistics for rentals.

Business Logic:
- Calculate rental statistics and metrics
- Track revenue and usage patterns
- Identify popular packages and stations
- Analyze user rental behavior
- Generate reports for admin dashboards

Author: Service Splitter (Cleaned)
Date: 2025-10-17
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any, Tuple, Optional
from decimal import Decimal
from django.db.models import Count, Sum
from django.utils import timezone

from api.common.services.base import BaseService
from api.user.rentals.models import Rental

if TYPE_CHECKING:
    from datetime import datetime


class RentalAnalyticsService(BaseService):
    """Service for rental analytics and statistics"""
    
    def get_rental_analytics(
        self,
        date_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive rental analytics for a date range.
        
        Args:
            date_range: Optional tuple of (start_date, end_date)
                       Defaults to last 30 days if not provided
        
        Returns:
            Dictionary containing:
                - Rental counts (total, active, completed, cancelled, overdue)
                - Revenue statistics
                - Duration averages
                - Return rate metrics
                - Popular packages and stations
                - Time-based breakdowns (hourly, daily, monthly)
        """
        try:
            # Determine date range
            if date_range:
                start_date, end_date = date_range
            else:
                # Default to last 30 days
                end_date = timezone.now()
                start_date = end_date - timezone.timedelta(days=30)
            
            # Filter rentals by date range
            rentals = Rental.objects.filter(
                created_at__range=(start_date, end_date)
            )
            
            # Calculate basic statistics
            stats = self._calculate_basic_stats(rentals)
            revenue = self._calculate_revenue_stats(rentals)
            duration_stats = self._calculate_duration_stats(rentals)
            return_stats = self._calculate_return_rate(rentals)
            popular_data = self._get_popular_items(rentals)
            
            # Combine all statistics
            return {
                **stats,
                **revenue,
                **duration_stats,
                **return_stats,
                **popular_data,
                # Placeholder for time-based breakdowns
                'hourly_breakdown': [],
                'daily_breakdown': [],
                'monthly_breakdown': []
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get rental analytics")
    
    def _calculate_basic_stats(self, rentals) -> Dict[str, int]:
        """Calculate basic rental count statistics"""
        return {
            'total_rentals': rentals.count(),
            'active_rentals': rentals.filter(status='ACTIVE').count(),
            'completed_rentals': rentals.filter(status='COMPLETED').count(),
            'cancelled_rentals': rentals.filter(status='CANCELLED').count(),
            'overdue_rentals': rentals.filter(status='OVERDUE').count(),
        }
    
    def _calculate_revenue_stats(self, rentals) -> Dict[str, Decimal]:
        """Calculate revenue statistics"""
        total_revenue = rentals.filter(
            payment_status='PAID'
        ).aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0')
        
        return {
            'total_revenue': total_revenue
        }
    
    def _calculate_duration_stats(self, rentals) -> Dict[str, float]:
        """Calculate rental duration statistics"""
        completed = rentals.filter(
            status='COMPLETED',
            started_at__isnull=False,
            ended_at__isnull=False
        )
        
        if not completed.exists():
            return {'average_rental_duration': 0.0}
        
        # Calculate durations in minutes
        durations = []
        for rental in completed:
            duration = rental.ended_at - rental.started_at
            durations.append(duration.total_seconds() / 60)
        
        average = sum(durations) / len(durations)
        
        return {
            'average_rental_duration': round(average, 1)
        }
    
    def _calculate_return_rate(self, rentals) -> Dict[str, float]:
        """Calculate timely return rate"""
        completed = rentals.filter(status='COMPLETED').count()
        
        if completed == 0:
            return {'timely_return_rate': 0.0}
        
        timely = rentals.filter(is_returned_on_time=True).count()
        rate = (timely / completed) * 100
        
        return {
            'timely_return_rate': round(rate, 1)
        }
    
    def _get_popular_items(self, rentals) -> Dict[str, list]:
        """Get popular packages and stations"""
        # Popular packages (top 5)
        popular_packages = list(
            rentals.values('package__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        # Popular stations (top 5)
        popular_stations = list(
            rentals.values('station__station_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        return {
            'popular_packages': popular_packages,
            'popular_stations': popular_stations
        }
