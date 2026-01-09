"""
🔄 Legacy NotificationService - Backward Compatibility
====================================================

This service provides the legacy API that views and other services expect.
It bridges the gap between old API and new clean notify system.
"""
from __future__ import annotations

from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q, Count

from api.common.services.base import BaseService
from api.user.notifications.models import Notification
from api.user.notifications.services.notify import NotifyService

User = get_user_model()

class NotificationService(BaseService):
    """
    Legacy NotificationService for backward compatibility
    
    This service provides the old API that views and bulk services expect,
    while internally using the new clean notify system where possible.
    """
    
    def __init__(self):
        super().__init__()
        self.notify_service = NotifyService()
    
    def create_notification(self, user, title: str, message: str, notification_type: str, 
                          data: Dict[str, Any] = None, channel: str = 'in_app',
                          template_slug: str = None, auto_send: bool = True) -> Notification:
        """Legacy method for creating notifications"""
        try:
            if template_slug:
                # Use new clean API if template is provided
                return self.notify_service.send(user, template_slug, **(data or {}))
            else:
                # Fallback to direct creation for backward compatibility
                notification = Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    data=data or {},
                    channel=channel
                )
                
                if auto_send and channel != 'in_app':
                    # Send via other channels if needed
                    self._send_via_channels(user, title, message, notification_type, data or {})
                
                return notification
                
        except Exception as e:
            self.handle_service_error(e, "Failed to create notification")
    
    def get_user_notifications(self, user, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get user notifications with pagination and filtering"""
        try:
            queryset = Notification.objects.filter(user=user)
            
            # Apply filters
            if filters:
                if filters.get('notification_type'):
                    queryset = queryset.filter(notification_type=filters['notification_type'])
                
                if filters.get('channel'):
                    queryset = queryset.filter(channel=filters['channel'])
                
                if filters.get('is_read') is not None:
                    queryset = queryset.filter(is_read=filters['is_read'])
            
            # Pagination
            page = filters.get('page', 1) if filters else 1
            page_size = filters.get('page_size', 20) if filters else 20
            
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            return {
                'results': list(page_obj.object_list),
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get user notifications")
    
    def get_notification_stats(self, user) -> Dict[str, Any]:
        """Get notification statistics for user - OPTIMIZED to use single query"""
        try:
            # Time calculations
            now = timezone.now()
            start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_week = start_of_today - timezone.timedelta(days=now.weekday())
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Single optimized query with all aggregations
            stats = Notification.objects.filter(user=user).aggregate(
                # Overall counts
                total_notifications=Count('id'),
                unread_count=Count('id', filter=Q(is_read=False)),
                read_count=Count('id', filter=Q(is_read=True)),
                
                # Time-based counts
                notifications_today=Count('id', filter=Q(created_at__gte=start_of_today)),
                notifications_this_week=Count('id', filter=Q(created_at__gte=start_of_week)),
                notifications_this_month=Count('id', filter=Q(created_at__gte=start_of_month)),
                
                # Type breakdown
                rental_notifications=Count('id', filter=Q(notification_type=Notification.NotificationTypeChoices.RENTAL)),
                payment_notifications=Count('id', filter=Q(notification_type=Notification.NotificationTypeChoices.PAYMENT)),
                promotion_notifications=Count('id', filter=Q(notification_type=Notification.NotificationTypeChoices.PROMOTION)),
                system_notifications=Count('id', filter=Q(notification_type=Notification.NotificationTypeChoices.SYSTEM)),
                achievement_notifications=Count('id', filter=Q(notification_type=Notification.NotificationTypeChoices.ACHIEVEMENT)),
                
                # Channel breakdown
                in_app_notifications=Count('id', filter=Q(channel=Notification.ChannelChoices.IN_APP)),
                push_notifications=Count('id', filter=Q(channel=Notification.ChannelChoices.PUSH)),
                sms_notifications=Count('id', filter=Q(channel=Notification.ChannelChoices.SMS)),
                email_notifications=Count('id', filter=Q(channel=Notification.ChannelChoices.EMAIL)),
            )

            # Return with None coalescing
            return {
                'total_notifications': stats['total_notifications'] or 0,
                'unread_count': stats['unread_count'] or 0,
                'read_count': stats['read_count'] or 0,
                'notifications_today': stats['notifications_today'] or 0,
                'notifications_this_week': stats['notifications_this_week'] or 0,
                'notifications_this_month': stats['notifications_this_month'] or 0,
                'rental_notifications': stats['rental_notifications'] or 0,
                'payment_notifications': stats['payment_notifications'] or 0,
                'promotion_notifications': stats['promotion_notifications'] or 0,
                'system_notifications': stats['system_notifications'] or 0,
                'achievement_notifications': stats['achievement_notifications'] or 0,
                'in_app_notifications': stats['in_app_notifications'] or 0,
                'push_notifications': stats['push_notifications'] or 0,
                'sms_notifications': stats['sms_notifications'] or 0,
                'email_notifications': stats['email_notifications'] or 0,
            }
        
        except Exception as e:
            self.handle_service_error(e, "Failed to get notification stats")
    
    def get_by_id(self, notification_id: str) -> Notification:
        """Get notification by ID"""
        try:
            return Notification.objects.get(id=notification_id)
        except Notification.DoesNotExist:
            from api.common.exceptions.custom import NotFoundError
            raise NotFoundError("Notification not found")
        except Exception as e:
            self.handle_service_error(e, "Failed to get notification")
    
    @transaction.atomic
    def mark_as_read(self, notification_id: str, user) -> Notification:
        """Mark notification as read - optimized with direct update"""
        try:
            # Use direct update query for better performance
            updated_count = Notification.objects.filter(
                id=notification_id,
                user=user,
                is_read=False  # Only update if not already read
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
            
            # Fetch the notification for response (already in cache after update)
            notification = Notification.objects.get(id=notification_id, user=user)
            
            return notification
            
        except Notification.DoesNotExist:
            from api.common.exceptions.custom import NotFoundError
            raise NotFoundError("Notification not found")
        except Exception as e:
            self.handle_service_error(e, "Failed to mark notification as read")
    
    @transaction.atomic
    def mark_all_as_read(self, user) -> int:
        """Mark all user notifications as read"""
        try:
            updated_count = Notification.objects.filter(
                user=user, 
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
            
            return updated_count
            
        except Exception as e:
            self.handle_service_error(e, "Failed to mark all notifications as read")
    
    @transaction.atomic
    def delete_notification(self, notification_id: str, user) -> bool:
        """Delete user notification"""
        try:
            deleted_count, _ = Notification.objects.filter(
                id=notification_id, 
                user=user
            ).delete()
            
            return deleted_count > 0
            
        except Exception as e:
            self.handle_service_error(e, "Failed to delete notification")
    
    def _send_via_channels(self, user, title: str, message: str, notification_type: str, data: Dict[str, Any]):
        """Send notification via other channels (FCM, SMS, Email)"""
        try:
            # Use the new notify service's channel distribution
            self.notify_service._distribute_channels(user, title, message, notification_type, data)
        except Exception as e:
            self.log_error(f"Failed to send via channels: {str(e)}")