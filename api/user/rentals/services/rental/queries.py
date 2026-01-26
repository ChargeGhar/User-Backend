"""
Rental Query Service
====================

Handles rental queries, history, and statistics.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from decimal import Decimal

from django.db.models import Count, Sum

from api.common.utils.helpers import paginate_queryset
from api.user.rentals.models import Rental


class RentalQueryMixin:
    """Mixin for rental query operations"""
    
    def get_user_rentals(self, user, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get user's rental history with filters"""
        try:
            queryset = Rental.objects.filter(user=user).select_related(
                'station', 'return_station', 'package', 'power_bank'
            )
            
            if filters:
                queryset = self._apply_rental_filters(queryset, filters)
            
            queryset = queryset.order_by('-created_at')
            
            page = filters.get('page', 1) if filters else 1
            page_size = filters.get('page_size', 20) if filters else 20
            
            return paginate_queryset(queryset, page, page_size)
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get user rentals")
    
    def _apply_rental_filters(self, queryset, filters: Dict[str, Any]):
        """Apply filters to rental queryset"""
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('payment_status'):
            queryset = queryset.filter(payment_status=filters['payment_status'])
        
        if filters.get('start_date'):
            queryset = queryset.filter(created_at__gte=filters['start_date'])
        
        if filters.get('end_date'):
            queryset = queryset.filter(created_at__lte=filters['end_date'])
        
        if filters.get('station_id'):
            queryset = queryset.filter(station_id=filters['station_id'])
        
        return queryset
    
    def get_active_rental(self, user) -> Optional[Rental]:
        """Get user's active rental (including overdue rentals that haven't been returned yet)"""
        try:
            return Rental.objects.filter(
                user=user,
                status__in=['PENDING', 'PENDING_POPUP', 'ACTIVE', 'OVERDUE']
            ).select_related('station', 'package', 'power_bank').first()
        except Exception as e:
            self.handle_service_error(e, "Failed to get active rental")
    
    def get_rental_stats(self, user) -> Dict[str, Any]:
        """Get user's rental statistics"""
        try:
            rentals = Rental.objects.filter(user=user)
            
            stats = self._get_basic_counts(rentals)
            stats.update(self._get_financial_stats(rentals))
            stats.update(self._get_time_stats(rentals, stats['completed_rentals']))
            stats.update(self._get_return_stats(rentals, stats['completed_rentals']))
            stats.update(self._get_favorites(rentals))
            stats.update(self._get_date_stats(rentals))
            
            return stats
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get rental stats")
    
    def _get_basic_counts(self, rentals) -> Dict[str, int]:
        """Get basic rental counts"""
        return {
            'total_rentals': rentals.count(),
            'completed_rentals': rentals.filter(status='COMPLETED').count(),
            'active_rentals': rentals.filter(status__in=['PENDING', 'PENDING_POPUP', 'ACTIVE']).count(),
            'cancelled_rentals': rentals.filter(status='CANCELLED').count(),
        }
    
    def _get_financial_stats(self, rentals) -> Dict[str, Decimal]:
        """Get financial statistics"""
        total_spent = rentals.filter(payment_status='PAID').aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0')
        
        return {'total_spent': total_spent}
    
    def _get_time_stats(self, rentals, completed_count: int) -> Dict[str, Any]:
        """Get time-based statistics"""
        completed_with_time = rentals.filter(
            status='COMPLETED',
            started_at__isnull=False,
            ended_at__isnull=False
        )
        
        total_time_used = 0
        if completed_with_time.exists():
            for rental in completed_with_time:
                duration = rental.ended_at - rental.started_at
                total_time_used += int(duration.total_seconds() / 60)
        
        average_duration = total_time_used / completed_count if completed_count > 0 else 0
        
        return {
            'total_time_used': total_time_used,
            'average_rental_duration': round(average_duration, 1),
        }
    
    def _get_return_stats(self, rentals, completed_count: int) -> Dict[str, Any]:
        """Get return statistics"""
        timely_returns = rentals.filter(is_returned_on_time=True).count()
        late_returns = completed_count - timely_returns
        timely_return_rate = (timely_returns / completed_count * 100) if completed_count > 0 else 0
        
        return {
            'timely_returns': timely_returns,
            'late_returns': late_returns,
            'timely_return_rate': round(timely_return_rate, 1),
        }
    
    def _get_favorites(self, rentals) -> Dict[str, Optional[str]]:
        """Get favorite station and package"""
        favorite_station = rentals.values('station__station_name').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        favorite_package = rentals.values('package__name').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        return {
            'favorite_station': favorite_station['station__station_name'] if favorite_station else None,
            'favorite_package': favorite_package['package__name'] if favorite_package else None,
        }
    
    def _get_date_stats(self, rentals) -> Dict[str, Any]:
        """Get first and last rental dates"""
        first_rental = rentals.order_by('created_at').first()
        last_rental = rentals.order_by('-created_at').first()
        
        return {
            'first_rental_date': first_rental.created_at if first_rental else None,
            'last_rental_date': last_rental.created_at if last_rental else None,
        }
