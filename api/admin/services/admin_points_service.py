"""
Service for admin points management
============================================================

This module contains service classes for admin points management operations.
Delegates core points logic to the points PointsService for consistency.

Created: 2025-11-11
"""
from __future__ import annotations

from typing import Dict, Any
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone

from api.common.services.base import CRUDService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.admin.models import AdminActionLog
from api.user.points.models import PointsTransaction
from api.user.auth.models import User


class AdminPointsService(CRUDService):
    """Service for admin points management"""
    model = PointsTransaction
    
    def __init__(self):
        super().__init__()
        from api.user.points.services import PointsService
        self.points_service = PointsService()
    
    @transaction.atomic
    def adjust_user_points(
        self, 
        user_id: str, 
        points: int, 
        adjustment_type: str, 
        reason: str, 
        admin_user
    ) -> Dict[str, Any]:
        """
        Adjust user points (add or deduct)
        
        Args:
            user_id: User ID to adjust points for
            points: Number of points to adjust
            adjustment_type: 'ADD' or 'DEDUCT'
            reason: Reason for adjustment
            admin_user: Admin user making the adjustment
            
        Returns:
            Dict with adjustment details
        """
        try:
            # Get user
            user = User.objects.get(id=user_id)
            
            # Use core points service for adjustment
            points_transaction = self.points_service.adjust_points(
                user=user,
                points=points,
                adjustment_type=adjustment_type,
                reason=reason,
                admin_user=admin_user
            )
            
            # Log admin action
            self._log_admin_action(
                admin_user=admin_user,
                action_type='ADJUST_USER_POINTS',
                target_model='User',
                target_id=str(user.id),
                changes={
                    'adjustment_type': adjustment_type,
                    'points': points,
                    'reason': reason,
                    'balance_before': points_transaction.balance_before,
                    'balance_after': points_transaction.balance_after
                },
                description=f"Adjusted points for {user.username}: {adjustment_type} {points} points"
            )
            
            # Send notification to user
            from api.user.notifications.services import notify
            notify(
                user=user,
                template_slug='admin_points_adjustment',
                async_send=True,
                adjustment_type=adjustment_type.lower(),
                points=points,
                reason=reason,
                new_balance=points_transaction.balance_after
            )
            
            self.log_info(
                f"Admin {admin_user.username} adjusted points for {user.username}: "
                f"{adjustment_type} {points}"
            )
            
            return {
                'transaction_id': str(points_transaction.id),
                'user_id': str(user.id),
                'username': user.username,
                'adjustment_type': adjustment_type,
                'points': points,
                'balance_before': points_transaction.balance_before,
                'balance_after': points_transaction.balance_after,
                'reason': reason,
                'adjusted_by': admin_user.username,
                'adjusted_at': points_transaction.created_at
            }
            
        except User.DoesNotExist:
            raise ServiceException(
                detail="User not found",
                code="user_not_found",
                status_code=404,
                user_message="The specified user does not exist"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to adjust user points")
    
    def get_points_analytics(
        self, 
        start_date=None, 
        end_date=None
    ) -> Dict[str, Any]:
        """
        Get comprehensive points analytics
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dict with points analytics
        """
        try:
            # Base queryset
            queryset = PointsTransaction.objects.all()
            
            # Apply date filters
            if start_date:
                queryset = queryset.filter(created_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(created_at__lte=end_date)
            
            # Total statistics
            total_transactions = queryset.count()
            
            earned_stats = queryset.filter(transaction_type='EARNED').aggregate(
                total_earned=Sum('points'),
                count=Count('id')
            )
            
            spent_stats = queryset.filter(transaction_type='SPENT').aggregate(
                total_spent=Sum('points'),
                count=Count('id')
            )
            
            adjustment_stats = queryset.filter(transaction_type='ADJUSTMENT').aggregate(
                total_adjusted=Sum('points'),
                count=Count('id')
            )
            
            # Points by source breakdown
            source_breakdown = queryset.filter(
                transaction_type='EARNED'
            ).values('source').annotate(
                total_points=Sum('points'),
                transaction_count=Count('id')
            ).order_by('-total_points')
            
            # Top users by points earned
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            top_earners = User.objects.filter(
                id__in=queryset.filter(transaction_type='EARNED').values_list('user_id', flat=True)
            ).annotate(
                total_earned=Sum('points_transactions__points', 
                               filter=Q(points_transactions__transaction_type='EARNED'))
            ).order_by('-total_earned')[:10]
            
            top_earners_data = [
                {
                    'user_id': str(user.id),
                    'username': user.username,
                    'total_earned': user.total_earned or 0
                }
                for user in top_earners
            ]
            
            # Recent activity (last 7 days)
            from datetime import timedelta
            last_7_days = timezone.now() - timedelta(days=7)
            recent_activity = queryset.filter(
                created_at__gte=last_7_days
            ).values('transaction_type').annotate(
                total_points=Sum('points'),
                count=Count('id')
            )
            
            return {
                'total_transactions': total_transactions,
                'earned': {
                    'total_points': earned_stats['total_earned'] or 0,
                    'transaction_count': earned_stats['count']
                },
                'spent': {
                    'total_points': spent_stats['total_spent'] or 0,
                    'transaction_count': spent_stats['count']
                },
                'adjustments': {
                    'total_points': adjustment_stats['total_adjusted'] or 0,
                    'transaction_count': adjustment_stats['count']
                },
                'source_breakdown': list(source_breakdown),
                'top_earners': top_earners_data,
                'recent_activity': list(recent_activity),
                'period': {
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get points analytics")
    
    def get_user_points_history(
        self, 
        user_id: str, 
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get points transaction history for a specific user
        
        Args:
            user_id: User ID to get history for
            filters: Optional filters (transaction_type, source, date range, pagination)
            
        Returns:
            Paginated points transaction history
        """
        try:
            # Get user
            user = User.objects.get(id=user_id)
            
            # Use core points service for history
            history = self.points_service.get_points_history(user, filters)
            
            return history
            
        except User.DoesNotExist:
            raise ServiceException(
                detail="User not found",
                code="user_not_found",
                status_code=404,
                user_message="The specified user does not exist"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get user points history")
    
    def get_all_points_history(
        self, 
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get points transaction history for all users
        
        Args:
            filters: Optional filters (user, transaction_type, source, date range, pagination)
            
        Returns:
            Paginated points transaction history
        """
        try:
            # Base queryset with optimizations
            queryset = PointsTransaction.objects.select_related(
                'user', 'related_rental', 'related_referral'
            )
            
            # Apply filters
            if filters:
                # Search by user ID, username, email, or description
                if filters.get('search'):
                    search_term = filters['search']
                    search_filters = (
                        Q(user__username__icontains=search_term) |
                        Q(user__email__icontains=search_term) |
                        Q(description__icontains=search_term)
                    )
                    
                    # If search term is a number, also search by user ID
                    if search_term.isdigit():
                        search_filters |= Q(user_id=int(search_term))
                    
                    queryset = queryset.filter(search_filters)
                
                # Transaction type filter
                if filters.get('transaction_type'):
                    queryset = queryset.filter(transaction_type=filters['transaction_type'])
                
                # Source filter
                if filters.get('source'):
                    queryset = queryset.filter(source=filters['source'])
                
                # Date range filters
                if filters.get('start_date'):
                    queryset = queryset.filter(created_at__gte=filters['start_date'])
                
                if filters.get('end_date'):
                    queryset = queryset.filter(created_at__lte=filters['end_date'])
            
            # Order by latest first
            queryset = queryset.order_by('-created_at')
            
            # Pagination
            page = filters.get('page', 1) if filters else 1
            page_size = filters.get('page_size', 20) if filters else 20
            
            return paginate_queryset(queryset, page, page_size)
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get points history")
    
    def _log_admin_action(
        self, 
        admin_user, 
        action_type: str, 
        target_model: str,
        target_id: str, 
        changes: Dict[str, Any], 
        description: str = ""
    ) -> None:
        """Log admin action for audit trail"""
        try:
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type=action_type,
                target_model=target_model,
                target_id=target_id,
                changes=changes,
                description=description,
                ip_address="127.0.0.1",  # Should be passed from request
                user_agent="Admin Panel"  # Should be passed from request
            )
        except Exception as e:
            self.log_error(f"Failed to log admin action: {str(e)}")
