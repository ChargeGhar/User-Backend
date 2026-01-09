"""
🎯 Points Tasks - Clean Celery Tasks for Points Operations
===========================================================

Simplified, universal tasks for points operations.
Following the same clean architecture as notifications app.

Usage:
    from api.user.points.tasks import award_points_task
    
    # Async
    award_points_task.delay(user_id, points, source, description)
"""

from __future__ import annotations

import logging
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import Dict, Any

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(
    name='points.award_points',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def award_points_task(self, user_id: str, points: int, source: str, 
                     description: str, metadata: Dict[str, Any] = None):
    """
    Award points to user asynchronously
    
    Args:
        user_id: User ID (UUID string)
        points: Points to award
        source: Source of points (e.g., 'RENTAL', 'TOPUP', 'REFERRAL')
        description: Description of the award
        metadata: Additional metadata (optional)
    
    Example:
        award_points_task.delay(
            user_id=str(user.id),
            points=50,
            source='RENTAL',
            description='Completed rental successfully',
            metadata={'rental_id': rental_id}
        )
    """
    try:
        from api.user.points.services import award_points
        
        # Get user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User not found: {user_id}")
            return {'status': 'failed', 'error': 'User not found'}
        
        # Award points using universal API
        transaction = award_points(
            user=user,
            points=points,
            source=source,
            description=description,
            async_send=False,  # We're already in async context
            metadata=metadata or {}
        )
        
        logger.info(f"Points awarded async: {user.username} +{points} ({source})")
        return {
            'status': 'success',
            'user_id': user_id,
            'points_awarded': points,
            'new_balance': transaction.balance_after,
            'transaction_id': str(transaction.id)
        }
        
    except Exception as e:
        logger.error(f"Failed to award points async: {str(e)}", exc_info=True)
        
        # Retry task on failure
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for award_points_task")
            return {'status': 'failed', 'error': str(e)}


@shared_task(
    name='points.deduct_points',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def deduct_points_task(self, user_id: str, points: int, source: str, 
                      description: str, metadata: Dict[str, Any] = None):
    """
    Deduct points from user asynchronously
    
    Args:
        user_id: User ID (UUID string)
        points: Points to deduct
        source: Source of deduction (e.g., 'REDEMPTION', 'PENALTY')
        description: Description of the deduction
        metadata: Additional metadata (optional)
    
    Example:
        deduct_points_task.delay(
            user_id=str(user.id),
            points=100,
            source='REDEMPTION',
            description='Redeemed discount coupon',
            metadata={'coupon_code': 'SAVE100'}
        )
    """
    try:
        from api.user.points.services import deduct_points
        
        # Get user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User not found: {user_id}")
            return {'status': 'failed', 'error': 'User not found'}
        
        # Deduct points using universal API
        transaction = deduct_points(
            user=user,
            points=points,
            source=source,
            description=description,
            async_send=False,  # We're already in async context
            **(metadata or {})
        )
        
        logger.info(f"Points deducted async: {user.username} -{points} ({source})")
        return {
            'status': 'success',
            'user_id': user_id,
            'points_deducted': points,
            'new_balance': transaction.balance_after,
            'transaction_id': str(transaction.id)
        }
        
    except Exception as e:
        logger.error(f"Failed to deduct points async: {str(e)}", exc_info=True)
        
        # Retry task on failure
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for deduct_points_task")
            return {'status': 'failed', 'error': str(e)}


@shared_task(
    name='points.complete_referral',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def complete_referral_task(self, referral_id: str):
    """
    Complete referral after first rental
    
    Args:
        referral_id: Referral ID (UUID string)
    
    Example:
        complete_referral_task.delay(referral_id=str(referral.id))
    """
    try:
        from api.user.points.services.referral_service import ReferralService
        
        service = ReferralService()
        result = service.complete_referral(referral_id)
        
        logger.info(f"Referral completed async: {referral_id}")
        return {
            'status': 'success',
            'referral_id': referral_id,
            **result
        }
        
    except Exception as e:
        logger.error(f"Failed to complete referral async: {str(e)}", exc_info=True)
        
        # Retry task on failure
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for complete_referral_task")
            return {'status': 'failed', 'error': str(e)}


@shared_task(
    name='points.expire_old_referrals',
    bind=True
)
def expire_old_referrals_task(self):
    """
    Expire old pending referrals (scheduled task)
    
    Example:
        # In celery beat schedule:
        'expire-old-referrals': {
            'task': 'points.expire_old_referrals',
            'schedule': crontab(hour=0, minute=0),  # Daily at midnight
        }
    """
    try:
        from api.user.points.services.referral_service import ReferralService
        
        service = ReferralService()
        expired_count = service.expire_old_referrals()
        
        logger.info(f"Expired {expired_count} old referrals")
        return {
            'status': 'success',
            'expired_count': expired_count
        }
        
    except Exception as e:
        logger.error(f"Failed to expire old referrals: {str(e)}", exc_info=True)
        return {'status': 'failed', 'error': str(e)}


@shared_task(
    name='points.calculate_leaderboard',
    bind=True
)
def calculate_leaderboard_task(self, limit: int = 100):
    """
    Calculate and cache points leaderboard (scheduled task)
    
    Args:
        limit: Number of top users to include
    
    Example:
        # In celery beat schedule:
        'calculate-leaderboard': {
            'task': 'points.calculate_leaderboard',
            'schedule': crontab(minute='*/30'),  # Every 30 minutes
        }
    """
    try:
        from api.user.points.services.points_leaderboard_service import PointsLeaderboardService
        from django.core.cache import cache
        
        service = PointsLeaderboardService()
        leaderboard = service.get_points_leaderboard(limit=limit)
        
        # Cache the leaderboard
        current_month = timezone.now().strftime('%Y-%m')
        cache_key = f"points_leaderboard:{current_month}"
        cache.set(cache_key, leaderboard, timeout=3600)  # 1 hour
        
        logger.info(f"Leaderboard calculated with {len(leaderboard)} users")
        return {
            'status': 'success',
            'leaderboard_size': len(leaderboard),
            'cache_key': cache_key
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate leaderboard: {str(e)}", exc_info=True)
        return {'status': 'failed', 'error': str(e)}


@shared_task(
    name='points.cleanup_old_transactions',
    bind=True
)
def cleanup_old_transactions_task(self, days: int = 730):
    """
    Clean up old points transactions (scheduled task)
    
    Args:
        days: Delete transactions older than this many days (default: 730 = 2 years)
    
    Example:
        # In celery beat schedule:
        'cleanup-old-transactions': {
            'task': 'points.cleanup_old_transactions',
            'schedule': crontab(day_of_month=1, hour=2),  # Monthly at 2 AM
        }
    """
    try:
        from api.user.points.models import PointsTransaction
        
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Only delete non-critical transactions
        deleted_count, _ = PointsTransaction.objects.filter(
            created_at__lt=cutoff_date,
            related_referral__isnull=True,
            source__in=['TOPUP', 'RENTAL', 'TIMELY_RETURN']
        ).delete()
        
        logger.info(f"Cleaned up {deleted_count} old points transactions")
        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old transactions: {str(e)}", exc_info=True)
        return {'status': 'failed', 'error': str(e)}


# Export all tasks
__all__ = [
    'award_points_task',
    'deduct_points_task',
    'complete_referral_task',
    'expire_old_referrals_task',
    'calculate_leaderboard_task',
    'cleanup_old_transactions_task',
]
