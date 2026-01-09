"""
User Analytics Service
Provides analytics data for user growth, status distribution, and engagement metrics
"""
from decimal import Decimal
from datetime import timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from api.user.auth.models import User


class UserAnalyticsService:
    """Service for user analytics operations"""
    
    @staticmethod
    def get_user_analytics():
        """
        Get comprehensive user analytics data
        
        Returns:
            dict: User analytics data including growth chart and status breakdown
        """
        now = timezone.now()
        
        # Total users
        total_users = User.objects.count()
        
        # Active users: is_active=True AND logged in within last 30 days
        active_users = User.objects.filter(
            is_active=True,
            last_login__gte=now - timedelta(days=30)
        ).count()
        
        # Inactive users: is_active=True BUT no login in 30+ days
        inactive_users = User.objects.filter(
            is_active=True
        ).filter(
            Q(last_login__lt=now - timedelta(days=30)) |
            Q(last_login__isnull=True)
        ).count()
        
        # Suspended users: is_active=False
        suspended_users = User.objects.filter(is_active=False).count()
        
        # New users counts
        new_users_today = User.objects.filter(
            date_joined__date=now.date()
        ).count()
        
        new_users_this_week = User.objects.filter(
            date_joined__gte=now - timedelta(days=7)
        ).count()
        
        new_users_this_month = User.objects.filter(
            date_joined__gte=now - timedelta(days=30)
        ).count()
        
        # User growth chart - last 6 months
        six_months_ago = now - timedelta(days=180)
        user_growth = User.objects.filter(
            date_joined__gte=six_months_ago
        ).annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        # Format growth chart data
        growth_labels = []
        growth_data = []
        
        for entry in user_growth:
            month_str = entry['month'].strftime('%b %Y')
            growth_labels.append(month_str)
            growth_data.append(entry['count'])
        
        # If no data, provide empty structure
        if not growth_labels:
            growth_labels = ["No data"]
            growth_data = [0]
        
        return {
            'summary': {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'suspended_users': suspended_users,
                'new_users_today': new_users_today,
                'new_users_this_week': new_users_this_week,
                'new_users_this_month': new_users_this_month
            },
            'user_growth_chart': {
                'labels': growth_labels,
                'period': 'Last 6 months',
                'datasets': [{
                    'label': 'New Users',
                    'data': growth_data
                }]
            },
            'user_status_chart': {
                'labels': ['Active', 'Inactive', 'Suspended'],
                'values': [active_users, inactive_users, suspended_users]
            }
        }
