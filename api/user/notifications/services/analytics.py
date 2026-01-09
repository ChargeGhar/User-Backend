from __future__ import annotations

from typing import Dict, Any
from django.utils import timezone
from django.db.models import Count

from api.common.services.base import BaseService
from api.user.notifications.models import Notification, SMS_FCMLog

class NotificationAnalyticsService(BaseService):
    """Service for notification analytics and reporting"""
    
    def get_notification_analytics(self, date_range: tuple = None) -> Dict[str, Any]:
        """Get comprehensive notification analytics"""
        try:
            if date_range:
                start_date, end_date = date_range
            else:
                # Default to last 30 days
                end_date = timezone.now()
                start_date = end_date - timezone.timedelta(days=30)
            
            # Get notifications in date range
            notifications = Notification.objects.filter(
                created_at__range=(start_date, end_date)
            )
            
            # Get SMS/FCM logs in date range
            sms_fcm_logs = SMS_FCMLog.objects.filter(
                created_at__range=(start_date, end_date)
            )
            
            total_sent = notifications.count() + sms_fcm_logs.count()
            total_delivered = notifications.count() + sms_fcm_logs.filter(status='sent').count()
            total_read = notifications.filter(is_read=True).count()
            
            delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
            read_rate = (total_read / notifications.count() * 100) if notifications.count() > 0 else 0
            
            # Channel breakdown
            channel_stats = {}
            for choice in Notification.ChannelChoices:
                count = notifications.filter(channel=choice.value).count()
                channel_stats[choice.value] = count
            
            # Add SMS and FCM from logs
            channel_stats['sms'] = sms_fcm_logs.filter(notification_type='sms').count()
            channel_stats['fcm'] = sms_fcm_logs.filter(notification_type='fcm').count()
            
            # Type breakdown
            type_stats = {}
            for choice in Notification.NotificationTypeChoices:
                count = notifications.filter(notification_type=choice.value).count()
                type_stats[choice.value] = count
            
            # Daily breakdown
            daily_breakdown = []
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            while current_date <= end_date_only:
                day_notifications = notifications.filter(
                    created_at__date=current_date
                ).count()
                day_sms_fcm = sms_fcm_logs.filter(
                    created_at__date=current_date
                ).count()
                
                daily_breakdown.append({
                    'date': current_date.isoformat(),
                    'notifications': day_notifications,
                    'sms_fcm': day_sms_fcm,
                    'total': day_notifications + day_sms_fcm
                })
                
                current_date += timezone.timedelta(days=1)
            
            # Top performing notifications (most read)
            top_notifications = notifications.filter(
                is_read=True
            ).values(
                'notification_type', 'title'
            ).annotate(
                read_count=Count('id')
            ).order_by('-read_count')[:10]
            
            # Failed notifications
            failed_notifications = sms_fcm_logs.filter(status='failed').count()
            failure_rate = (failed_notifications / total_sent * 100) if total_sent > 0 else 0
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_sent': total_sent,
                'delivery_rate': round(delivery_rate, 2),
                'read_rate': round(read_rate, 2),
                'channel_stats': channel_stats,
                'type_stats': type_stats,
                'daily_breakdown': daily_breakdown,
                'top_notifications': list(top_notifications),
                'failed_notifications': failed_notifications,
                'failure_rate': round(failure_rate, 2)
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get notification analytics")
    
    def get_user_engagement_analytics(self, date_range: tuple = None) -> Dict[str, Any]:
        """Get user engagement analytics"""
        try:
            if date_range:
                start_date, end_date = date_range
            else:
                end_date = timezone.now()
                start_date = end_date - timezone.timedelta(days=30)
            
            notifications = Notification.objects.filter(
                created_at__range=(start_date, end_date)
            )
            
            # User engagement metrics
            total_users_notified = notifications.values('user').distinct().count()
            total_users_engaged = notifications.filter(is_read=True).values('user').distinct().count()
            
            engagement_rate = (total_users_engaged / total_users_notified * 100) if total_users_notified > 0 else 0
            
            # Average notifications per user
            avg_notifications_per_user = notifications.count() / total_users_notified if total_users_notified > 0 else 0
            
            # Most engaged users (by read count)
            most_engaged_users = notifications.filter(
                is_read=True
            ).values(
                'user__username'
            ).annotate(
                read_count=Count('id')
            ).order_by('-read_count')[:10]
            
            # Notification type preferences (by read rate)
            type_preferences = []
            for choice in Notification.NotificationTypeChoices:
                type_notifications = notifications.filter(notification_type=choice.value)
                total_type = type_notifications.count()
                read_type = type_notifications.filter(is_read=True).count()
                read_rate = (read_type / total_type * 100) if total_type > 0 else 0
                
                type_preferences.append({
                    'type': choice.value,
                    'total_sent': total_type,
                    'total_read': read_type,
                    'read_rate': round(read_rate, 2)
                })
            
            # Sort by read rate
            type_preferences.sort(key=lambda x: x['read_rate'], reverse=True)
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_users_notified': total_users_notified,
                'total_users_engaged': total_users_engaged,
                'engagement_rate': round(engagement_rate, 2),
                'avg_notifications_per_user': round(avg_notifications_per_user, 2),
                'most_engaged_users': list(most_engaged_users),
                'type_preferences': type_preferences
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get user engagement analytics")
    
    def get_delivery_performance(self, date_range: tuple = None) -> Dict[str, Any]:
        """Get delivery performance metrics"""
        try:
            if date_range:
                start_date, end_date = date_range
            else:
                end_date = timezone.now()
                start_date = end_date - timezone.timedelta(days=7)  # Last 7 days
            
            sms_fcm_logs = SMS_FCMLog.objects.filter(
                created_at__range=(start_date, end_date)
            )
            
            # SMS performance
            sms_logs = sms_fcm_logs.filter(notification_type='sms')
            sms_total = sms_logs.count()
            sms_sent = sms_logs.filter(status='sent').count()
            sms_failed = sms_logs.filter(status='failed').count()
            sms_success_rate = (sms_sent / sms_total * 100) if sms_total > 0 else 0
            
            # FCM performance
            fcm_logs = sms_fcm_logs.filter(notification_type='fcm')
            fcm_total = fcm_logs.count()
            fcm_sent = fcm_logs.filter(status='sent').count()
            fcm_failed = fcm_logs.filter(status='failed').count()
            fcm_success_rate = (fcm_sent / fcm_total * 100) if fcm_total > 0 else 0
            
            # Overall performance
            total_external = sms_total + fcm_total
            total_external_sent = sms_sent + fcm_sent
            overall_success_rate = (total_external_sent / total_external * 100) if total_external > 0 else 0
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'sms_performance': {
                    'total': sms_total,
                    'sent': sms_sent,
                    'failed': sms_failed,
                    'success_rate': round(sms_success_rate, 2)
                },
                'fcm_performance': {
                    'total': fcm_total,
                    'sent': fcm_sent,
                    'failed': fcm_failed,
                    'success_rate': round(fcm_success_rate, 2)
                },
                'overall_performance': {
                    'total': total_external,
                    'sent': total_external_sent,
                    'failed': sms_failed + fcm_failed,
                    'success_rate': round(overall_success_rate, 2)
                }
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get delivery performance")