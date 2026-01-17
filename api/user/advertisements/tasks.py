"""
Advertisement Celery Tasks
=========================
Automated tasks for advertisement lifecycle management
"""
from __future__ import annotations

import logging
from typing import Dict, List

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from api.common.tasks.base import BaseTask
from api.user.advertisements.models import AdRequest

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(
    base=BaseTask,
    bind=True,
    name='advertisements.auto_start_scheduled_ads',
    queue='advertisements'
)
def auto_start_scheduled_ads(self) -> Dict:
    """
    Auto-start scheduled ads that have reached their start date.
    
    SCHEDULED: Runs every hour via Celery Beat
    
    Business Logic:
    - Find ads with status='SCHEDULED' and start_date <= today
    - Change status to 'RUNNING'
    - Log each transition
    
    Returns:
        dict: {
            'started_count': int,
            'started_ad_ids': List[str],
            'errors': List[dict]
        }
    """
    try:
        today = timezone.now().date()
        
        # Get ads that should start today or earlier
        ads_to_start = AdRequest.objects.filter(
            status='SCHEDULED',
            start_date__lte=today
        ).select_related('user')
        
        started_count = 0
        started_ad_ids = []
        errors = []
        
        for ad in ads_to_start:
            try:
                with transaction.atomic():
                    # Update status to RUNNING
                    ad.status = 'RUNNING'
                    ad.save(update_fields=['status', 'updated_at'])
                    
                    started_count += 1
                    started_ad_ids.append(str(ad.id))
                    
                    self.logger.info(
                        f"Auto-started ad: id={ad.id}, title={ad.title}, "
                        f"user={ad.user.email}, start_date={ad.start_date}"
                    )
                    
                    # Send notification to user
                    try:
                        from api.user.notifications.services import notify
                        notify(
                            ad.user,
                            'advertisement_started',
                            async_send=True,
                            ad_title=ad.title or 'Your Advertisement',
                            start_date=ad.start_date.isoformat(),
                            end_date=ad.end_date.isoformat() if ad.end_date else None
                        )
                    except Exception as notify_error:
                        self.logger.warning(
                            f"Failed to send start notification for ad {ad.id}: {notify_error}"
                        )
                        
            except Exception as ad_error:
                error_msg = f"Failed to start ad {ad.id}: {str(ad_error)}"
                self.logger.error(error_msg)
                errors.append({
                    'ad_id': str(ad.id),
                    'error': str(ad_error)
                })
        
        result = {
            'started_count': started_count,
            'started_ad_ids': started_ad_ids,
            'errors': errors,
            'checked_at': timezone.now().isoformat()
        }
        
        if started_count > 0:
            self.logger.info(
                f"Auto-started {started_count} ads: {', '.join(started_ad_ids)}"
            )
        else:
            self.logger.debug("No ads to start")
        
        return result
        
    except Exception as e:
        self.logger.error(f"Failed to auto-start scheduled ads: {str(e)}")
        raise


@shared_task(
    base=BaseTask,
    bind=True,
    name='advertisements.auto_complete_finished_ads',
    queue='advertisements'
)
def auto_complete_finished_ads(self) -> Dict:
    """
    Auto-complete running ads that have passed their end date.
    
    SCHEDULED: Runs every hour via Celery Beat
    
    Business Logic:
    - Find ads with status='RUNNING' and end_date < today
    - Change status to 'COMPLETED'
    - Set completed_at timestamp
    - Log each transition
    
    Returns:
        dict: {
            'completed_count': int,
            'completed_ad_ids': List[str],
            'errors': List[dict]
        }
    """
    try:
        today = timezone.now().date()
        
        # Get ads that should have ended before today
        ads_to_complete = AdRequest.objects.filter(
            status='RUNNING',
            end_date__lt=today
        ).select_related('user')
        
        completed_count = 0
        completed_ad_ids = []
        errors = []
        
        for ad in ads_to_complete:
            try:
                with transaction.atomic():
                    # Update status to COMPLETED and set completed_at
                    ad.status = 'COMPLETED'
                    ad.completed_at = timezone.now()
                    ad.save(update_fields=['status', 'completed_at', 'updated_at'])
                    
                    completed_count += 1
                    completed_ad_ids.append(str(ad.id))
                    
                    self.logger.info(
                        f"Auto-completed ad: id={ad.id}, title={ad.title}, "
                        f"user={ad.user.email}, end_date={ad.end_date}"
                    )
                    
                    # Send notification to user
                    try:
                        from api.user.notifications.services import notify
                        notify(
                            ad.user,
                            'advertisement_completed',
                            async_send=True,
                            ad_title=ad.title or 'Your Advertisement',
                            start_date=ad.start_date.isoformat() if ad.start_date else None,
                            end_date=ad.end_date.isoformat(),
                            duration_days=ad.duration_days
                        )
                    except Exception as notify_error:
                        self.logger.warning(
                            f"Failed to send completion notification for ad {ad.id}: {notify_error}"
                        )
                        
            except Exception as ad_error:
                error_msg = f"Failed to complete ad {ad.id}: {str(ad_error)}"
                self.logger.error(error_msg)
                errors.append({
                    'ad_id': str(ad.id),
                    'error': str(ad_error)
                })
        
        result = {
            'completed_count': completed_count,
            'completed_ad_ids': completed_ad_ids,
            'errors': errors,
            'checked_at': timezone.now().isoformat()
        }
        
        if completed_count > 0:
            self.logger.info(
                f"Auto-completed {completed_count} ads: {', '.join(completed_ad_ids)}"
            )
        else:
            self.logger.debug("No ads to complete")
        
        return result
        
    except Exception as e:
        self.logger.error(f"Failed to auto-complete finished ads: {str(e)}")
        raise


@shared_task(
    base=BaseTask,
    bind=True,
    name='advertisements.check_payment_pending_ads',
    queue='advertisements'
)
def check_payment_pending_ads(self) -> Dict:
    """
    Check for ads pending payment for too long and send reminders.
    
    SCHEDULED: Runs daily via Celery Beat
    
    Business Logic:
    - Find ads with status='PENDING_PAYMENT' for more than 24 hours
    - Send reminder notification to user
    - Log reminder sent
    
    Returns:
        dict: {
            'reminder_count': int,
            'reminded_ad_ids': List[str],
            'errors': List[dict]
        }
    """
    try:
        # Find ads pending payment for more than 24 hours
        cutoff_time = timezone.now() - timezone.timedelta(hours=24)
        
        pending_ads = AdRequest.objects.filter(
            status='PENDING_PAYMENT',
            approved_at__lt=cutoff_time
        ).select_related('user')
        
        reminder_count = 0
        reminded_ad_ids = []
        errors = []
        
        for ad in pending_ads:
            try:
                # Send reminder notification
                from api.user.notifications.services import notify
                notify(
                    ad.user,
                    'advertisement_payment_reminder',
                    async_send=True,
                    ad_title=ad.title or 'Your Advertisement',
                    admin_price=str(ad.admin_price),
                    approved_at=ad.approved_at.isoformat() if ad.approved_at else None
                )
                
                reminder_count += 1
                reminded_ad_ids.append(str(ad.id))
                
                self.logger.info(
                    f"Sent payment reminder for ad: id={ad.id}, "
                    f"user={ad.user.email}, price={ad.admin_price}"
                )
                
            except Exception as notify_error:
                error_msg = f"Failed to send reminder for ad {ad.id}: {str(notify_error)}"
                self.logger.error(error_msg)
                errors.append({
                    'ad_id': str(ad.id),
                    'error': str(notify_error)
                })
        
        result = {
            'reminder_count': reminder_count,
            'reminded_ad_ids': reminded_ad_ids,
            'errors': errors,
            'checked_at': timezone.now().isoformat()
        }
        
        if reminder_count > 0:
            self.logger.info(
                f"Sent {reminder_count} payment reminders"
            )
        else:
            self.logger.debug("No payment reminders needed")
        
        return result
        
    except Exception as e:
        self.logger.error(f"Failed to check payment pending ads: {str(e)}")
        raise


