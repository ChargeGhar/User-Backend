"""
🎯 Points API - Universal Points Operations
============================================

Simple, universal API for points operations.
Works for ANY scenario - no app-specific assumptions!

Usage:
    from api.user.points.services import award_points, deduct_points
    
    # Sync (immediate)
    award_points(user, 50, 'RENTAL', 'Completed rental')
    
    # Async (background)
    award_points(user, 50, 'RENTAL', 'Completed rental', async_send=True)
"""

from __future__ import annotations

from typing import Union
from api.user.points.models import PointsTransaction


# Direct service imports - no lazy loading needed
from api.user.points.services.points_service import PointsService
from api.user.points.services.referral_service import ReferralService

# Module-level service instances for efficiency
_points_service = PointsService()
_referral_service = ReferralService()


def award_points(user, points: int, source: str, description: str, 
                async_send: bool = False, **metadata) -> Union[PointsTransaction, 'AsyncResult']:
    """
    🚀 Universal points awarding - Works for ALL scenarios
    
    Args:
        user: User object or user_id (str) for async
        points: Points to award
        source: Source of points (e.g., 'RENTAL', 'TOPUP', 'REFERRAL', 'SIGNUP')
        description: Description of the award
        async_send: If True, awards via Celery (non-blocking). If False, awards immediately.
        **metadata: Additional metadata (e.g., rental_id='123', topup_amount=500)
    
    Returns:
        - If async_send=False: Returns PointsTransaction object
        - If async_send=True: Returns Celery task result
    
    Examples:
        # Sync (immediate, blocking) - Use for critical operations
        award_points(user, 100, 'SIGNUP', 'Welcome bonus')
        award_points(user, 50, 'RENTAL', 'Completed rental', rental_id='R123')
        
        # Async (background, non-blocking) - Use for non-critical operations
        award_points(user, 10, 'TOPUP', 'Top-up reward', async_send=True, topup_amount=500)
        award_points(user, 25, 'REFERRAL', 'Referral bonus', async_send=True)
        
        # Works for ANY scenario - rental, payment, promotion, etc.
        award_points(user, 30, 'TIMELY_RETURN', 'Returned on time', async_send=True)
        award_points(user, 5, 'REVIEW', 'Left a review')
        award_points(user, 200, 'ACHIEVEMENT', 'Milestone reached')
    """
    if async_send:
        # Import here to avoid circular imports
        from api.user.points.tasks import award_points_task
        
        # Convert user to user_id if needed
        user_id = str(user.id) if hasattr(user, 'id') else str(user)
        
        # Send async via Celery
        return award_points_task.delay(
            user_id=user_id,
            points=points,
            source=source,
            description=description,
            metadata=metadata
        )
    else:
        # Send sync (immediate)
        return _points_service.award_points(
            user=user,
            points=points,
            source=source,
            description=description,
            metadata=metadata
        )


def deduct_points(user, points: int, source: str, description: str,
                 async_send: bool = False, **metadata) -> Union[PointsTransaction, 'AsyncResult']:
    """
    🚀 Universal points deduction - Works for ALL scenarios
    
    Args:
        user: User object or user_id (str) for async
        points: Points to deduct
        source: Source of deduction (e.g., 'REDEMPTION', 'PENALTY', 'REFUND')
        description: Description of the deduction
        async_send: If True, deducts via Celery (non-blocking). If False, deducts immediately.
        **metadata: Additional metadata (e.g., coupon_code='SAVE100', order_id='O123')
    
    Returns:
        - If async_send=False: Returns PointsTransaction object
        - If async_send=True: Returns Celery task result
    
    Examples:
        # Sync (immediate, blocking) - Use for critical operations
        deduct_points(user, 100, 'REDEMPTION', 'Redeemed discount', coupon_code='SAVE100')
        
        # Async (background, non-blocking) - Use for non-critical operations
        deduct_points(user, 50, 'PENALTY', 'Late return penalty', async_send=True)
        
        # Works for ANY scenario
        deduct_points(user, 20, 'REFUND', 'Refunded purchase', order_id='O123')
    """
    if async_send:
        # Import here to avoid circular imports
        from api.user.points.tasks import deduct_points_task
        
        # Convert user to user_id if needed
        user_id = str(user.id) if hasattr(user, 'id') else str(user)
        
        # Send async via Celery
        return deduct_points_task.delay(
            user_id=user_id,
            points=points,
            source=source,
            description=description,
            metadata=metadata
        )
    else:
        # Send sync (immediate)
        return _points_service.deduct_points(
            user=user,
            points=points,
            source=source,
            description=description,
            metadata=metadata
        )


def complete_referral(referral_id: str, async_send: bool = True):
    """
    🚀 Complete referral (usually async)
    
    Args:
        referral_id: Referral ID (UUID string)
        async_send: If True, completes via Celery. Default True for referrals.
    
    Returns:
        - If async_send=False: Returns dict with result
        - If async_send=True: Returns Celery task result
    
    Example:
        complete_referral(referral_id=str(referral.id))
    """
    if async_send:
        from api.user.points.tasks import complete_referral_task
        return complete_referral_task.delay(referral_id=referral_id)
    else:
        return _referral_service.complete_referral(referral_id)


__all__ = [
    'award_points',      # Universal sync/async points awarding
    'deduct_points',     # Universal sync/async points deduction
    'complete_referral', # Complete referral
]
