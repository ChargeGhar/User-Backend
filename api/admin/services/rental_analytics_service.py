"""
Rental Analytics Service
Provides analytics data for PowerBank rentals including status, payment methods, and trends
"""
from decimal import Decimal
from datetime import timedelta
from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncWeek
from django.utils import timezone

from api.rentals.models import Rental
from api.payments.models import Transaction


class RentalAnalyticsService:
    """Service for rental analytics operations"""
    
    @staticmethod
    def get_rental_analytics():
        """
        Get comprehensive rental analytics data
        
        Returns:
            dict: Rental analytics data including status, payment methods, and trends
        """
        # Rental status counts
        total_rentals = Rental.objects.count()
        active_rentals = Rental.objects.filter(status='ACTIVE').count()
        overdue_rentals = Rental.objects.filter(status='OVERDUE').count()
        completed_rentals = Rental.objects.filter(status='COMPLETED').count()
        cancelled_rentals = Rental.objects.filter(status='CANCELLED').count()
        
        # Payment methods for rentals
        rental_payment_methods = Transaction.objects.filter(
            status='SUCCESS',
            related_rental__isnull=False
        ).values('payment_method_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # Build payment method dict
        payment_method_data = {pm['payment_method_type']: pm for pm in rental_payment_methods}
        
        pm_labels = []
        pm_values = []
        pm_total = Decimal('0')
        
        for method in ['WALLET', 'GATEWAY', 'POINTS', 'COMBINATION']:
            data = payment_method_data.get(method, {'total': Decimal('0'), 'count': 0})
            amount = data['total'] or Decimal('0')
            pm_labels.append(method.title())
            pm_values.append(float(amount))
            pm_total += amount
        
        # Calculate percentages
        pm_percentages = []
        for i, value in enumerate(pm_values):
            if i == len(pm_values) - 1:
                # Last item ensures sum = 100%
                pct = round(100 - sum(pm_percentages), 2) if pm_total > 0 else 0
            else:
                pct = round((value / float(pm_total) * 100), 2) if pm_total > 0 else 0
            pm_percentages.append(pct)
        
        # Gateway breakdown for rentals
        gateway_transactions = Transaction.objects.filter(
            status='SUCCESS',
            related_rental__isnull=False,
            payment_method_type='GATEWAY'
        ).exclude(
            Q(gateway_reference__isnull=True) | Q(gateway_reference='')
        ).values('gateway_reference', 'amount')
        
        # Aggregate by gateway type
        gateway_summary = {}
        for txn in gateway_transactions:
            ref = (txn['gateway_reference'] or '').lower()
            gateway = None
            
            if 'khalti' in ref:
                gateway = 'Khalti'
            elif 'esewa' in ref:
                gateway = 'eSewa'
            elif 'stripe' in ref:
                gateway = 'Stripe'
            else:
                # Skip unrecognized patterns
                continue
            
            if gateway not in gateway_summary:
                gateway_summary[gateway] = {'count': 0, 'amount': Decimal('0')}
            
            gateway_summary[gateway]['count'] += 1
            gateway_summary[gateway]['amount'] += txn['amount']
        
        # Format gateway breakdown
        gateway_labels = []
        gateway_values = []
        gateway_counts = []
        gateway_total = sum(data['amount'] for data in gateway_summary.values())
        
        for gateway in ['Khalti', 'eSewa', 'Stripe']:
            if gateway in gateway_summary:
                gateway_labels.append(gateway)
                gateway_values.append(float(gateway_summary[gateway]['amount']))
                gateway_counts.append(gateway_summary[gateway]['count'])
        
        # Calculate gateway percentages
        gateway_percentages = []
        for i, value in enumerate(gateway_values):
            if i == len(gateway_values) - 1:
                pct = round(100 - sum(gateway_percentages), 2) if gateway_total > 0 else 0
            else:
                pct = round((value / float(gateway_total) * 100), 2) if gateway_total > 0 else 0
            gateway_percentages.append(pct)
        
        # Rental cycles (completed rentals only)
        completed = Rental.objects.filter(status='COMPLETED').exclude(
            Q(started_at__isnull=True) | Q(ended_at__isnull=True)
        )
        
        durations = []
        for rental in completed:
            duration_seconds = (rental.ended_at - rental.started_at).total_seconds()
            duration_minutes = duration_seconds / 60
            if duration_minutes > 0:
                durations.append(duration_minutes)
        
        if durations:
            average_duration = sum(durations) / len(durations)
            longest_duration = max(durations)
            shortest_duration = min(durations)
        else:
            average_duration = 0
            longest_duration = 0
            shortest_duration = 0
        
        # Format duration display
        def format_duration(minutes):
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            if hours > 0:
                return f"{hours}h {mins}m"
            return f"{mins}m"
        
        # Rental trend - last 4 weeks
        now = timezone.now()
        weeks = []
        week_labels = []
        week_data = []
        
        for i in range(3, -1, -1):  # 4 weeks ago to current week
            week_start = now - timedelta(days=(i + 1) * 7)
            week_end = now - timedelta(days=i * 7)
            
            week_count = Rental.objects.filter(
                created_at__gte=week_start,
                created_at__lt=week_end
            ).count()
            
            label = f"{week_start.strftime('%b %d')}-{week_end.strftime('%d')}"
            week_labels.append(label)
            week_data.append(week_count)
        
        return {
            'summary': {
                'total_rentals': total_rentals,
                'active_rentals': active_rentals,
                'overdue_rentals': overdue_rentals,
                'completed_rentals': completed_rentals,
                'cancelled_rentals': cancelled_rentals
            },
            'rental_status_chart': {
                'labels': ['Active', 'Overdue', 'Completed', 'Cancelled'],
                'values': [active_rentals, overdue_rentals, completed_rentals, cancelled_rentals]
            },
            'payment_methods_for_rentals': {
                'labels': pm_labels,
                'values': pm_values,
                'percentages': pm_percentages
            },
            'gateway_breakdown_for_rentals': {
                'labels': gateway_labels,
                'values': gateway_values,
                'counts': gateway_counts,
                'percentages': gateway_percentages
            },
            'rental_cycles': {
                'total_completed': len(durations),
                'duration_unit': 'minutes',
                'average_duration': round(average_duration, 2),
                'longest_duration': round(longest_duration, 2),
                'shortest_duration': round(shortest_duration, 2),
                'average_display': format_duration(average_duration),
                'longest_display': format_duration(longest_duration),
                'shortest_display': format_duration(shortest_duration)
            },
            'rental_trend_chart': {
                'labels': week_labels,
                'period': 'Last 4 weeks',
                'datasets': [{
                    'label': 'Rentals',
                    'data': week_data
                }]
            }
        }
