from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from api.common.tasks.base import BaseTask
from api.user.promotions.models import Coupon, CouponUsage


@shared_task(base=BaseTask, bind=True)
def cleanup_old_coupon_data(self):
    """
    Clean up old coupon usage data.

    Removes usage records for expired coupons older than 1 year.
    This task is scheduled to run weekly via Celery Beat.

    Returns:
        dict: Number of records deleted

    Example:
        # Scheduled in tasks/app.py
        'cleanup-old-coupon-data': {
            'task': 'api.promotions.tasks.cleanup_old_coupon_data',
            'schedule': 604800.0,  # Weekly
        }
    """
    try:
        # Clean up usage records for expired coupons older than 1 year
        one_year_ago = timezone.now() - timezone.timedelta(days=365)

        old_usages = CouponUsage.objects.filter(
            coupon__status=Coupon.StatusChoices.EXPIRED, used_at__lt=one_year_ago
        )

        deleted_count, _ = old_usages.delete()

        self.logger.info(f"Cleaned up {deleted_count} old coupon usage records")
        return {"deleted_count": deleted_count}

    except Exception as e:
        self.logger.error(f"Failed to cleanup old coupon data: {str(e)}")
        raise
