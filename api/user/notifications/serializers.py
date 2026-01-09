from __future__ import annotations

from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field

from api.user.notifications.models import (
    Notification, NotificationTemplate, NotificationRule, SMS_FCMLog
)
from api.common.serializers import BaseResponseSerializer

# MVP Pattern: List vs Detail Serializers





class NotificationListSerializer(serializers.ModelSerializer):
    """Minimal serializer for notification lists - MVP optimized"""
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'notification_type', 'is_read', 
            'created_at', 'time_ago'
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_time_ago(self, obj) -> str:
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days}d"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m"
        else:
            return "now"


class NotificationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for notifications - Full data"""
    time_ago = serializers.SerializerMethodField()
    is_recent = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'data',
            'channel', 'is_read', 'read_at', 'created_at',
            'time_ago', 'is_recent'
        ]
        read_only_fields = ['id', 'created_at']
    
    @extend_schema_field(serializers.CharField)
    def get_time_ago(self, obj) -> str:
        """Get human-readable time ago"""
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_recent(self, obj) -> bool:
        """Check if notification is recent (within 24 hours)"""
        return (timezone.now() - obj.created_at).days == 0


# Backward compatibility alias
NotificationSerializer = NotificationDetailSerializer


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating notification (mark as read)"""
    
    class Meta:
        model = Notification
        fields = ['is_read']
    
    def update(self, instance, validated_data):
        if validated_data.get('is_read') and not instance.is_read:
            instance.read_at = timezone.now()
        elif not validated_data.get('is_read') and instance.is_read:
            instance.read_at = None
        
        instance.is_read = validated_data.get('is_read', instance.is_read)
        instance.save(update_fields=['is_read', 'read_at'])
        return instance


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications (Admin/System use)"""
    
    class Meta:
        model = Notification
        fields = [
            'user', 'title', 'message', 'notification_type', 
            'data', 'channel'
        ]
    
    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters")
        return value.strip()
    
    def validate_message(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Message must be at least 5 characters")
        return value.strip()


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification templates"""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'slug', 'title_template', 'message_template',
            'notification_type', 'description', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters")
        return value.strip()
    
    def validate_title_template(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Title template must be at least 5 characters")
        return value.strip()
    
    def validate_message_template(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message template must be at least 10 characters")
        return value.strip()


class NotificationRuleSerializer(serializers.ModelSerializer):
    """Serializer for notification rules"""
    
    class Meta:
        model = NotificationRule
        fields = [
            'id', 'notification_type', 'send_in_app', 'send_push',
            'send_sms', 'send_email', 'is_critical', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_notification_type(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Notification type must be at least 3 characters")
        return value.strip()


class SMS_FCMLogSerializer(serializers.ModelSerializer):
    """Serializer for SMS/FCM logs"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    formatted_recipient = serializers.SerializerMethodField()
    status = serializers.ChoiceField(
        choices=SMS_FCMLog.StatusChoices.choices,
        help_text="Notification delivery status"
    )
    
    class Meta:
        model = SMS_FCMLog
        fields = [
            'id', 'title', 'message', 'notification_type', 'recipient',
            'status', 'response', 'sent_at', 'created_at',
            'user_username', 'formatted_recipient'
        ]
        read_only_fields = ['id', 'created_at', 'sent_at', 'status']
    
    def get_formatted_recipient(self, obj):
        """Format recipient for display (mask sensitive data)"""
        if obj.notification_type == 'sms':
            # Mask phone number
            if len(obj.recipient) > 4:
                return f"***{obj.recipient[-4:]}"
            return "***"
        else:
            # Mask FCM token
            if len(obj.recipient) > 8:
                return f"{obj.recipient[:4]}...{obj.recipient[-4:]}"
            return "***"


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    total_notifications = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    read_count = serializers.IntegerField()
    notifications_today = serializers.IntegerField()
    notifications_this_week = serializers.IntegerField()
    notifications_this_month = serializers.IntegerField()
    
    # Breakdown by type
    rental_notifications = serializers.IntegerField()
    payment_notifications = serializers.IntegerField()
    promotion_notifications = serializers.IntegerField()
    system_notifications = serializers.IntegerField()
    achievement_notifications = serializers.IntegerField()
    
    # Breakdown by channel
    in_app_notifications = serializers.IntegerField()
    push_notifications = serializers.IntegerField()
    sms_notifications = serializers.IntegerField()
    email_notifications = serializers.IntegerField()


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notifications (Admin)"""
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        max_length=1000,  # Max 1000 users at once
        required=False
    )
    user_filter = serializers.ChoiceField(
        choices=[
            ('all', 'All Users'),
            ('active', 'Active Users'),
            ('premium', 'Premium Users'),
            ('new', 'New Users (Last 30 days)'),
        ],
        required=False
    )
    title = serializers.CharField(max_length=255)
    message = serializers.CharField(max_length=1000)
    notification_type = serializers.ChoiceField(choices=Notification.NotificationTypeChoices.choices)
    data = serializers.JSONField(default=dict, required=False)
    send_push = serializers.BooleanField(default=False)
    send_in_app = serializers.BooleanField(default=True)
    
    def validate(self, attrs):
        if not attrs.get('user_ids') and not attrs.get('user_filter'):
            raise serializers.ValidationError("Either user_ids or user_filter must be provided")
        
        if attrs.get('user_ids') and attrs.get('user_filter'):
            raise serializers.ValidationError("Cannot specify both user_ids and user_filter")
        
        return attrs
    
    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters")
        return value.strip()
    
    def validate_message(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters")
        return value.strip()


class NotificationPreferencesSerializer(serializers.Serializer):
    """Serializer for user notification preferences"""
    rental_notifications = serializers.BooleanField(default=True)
    payment_notifications = serializers.BooleanField(default=True)
    promotion_notifications = serializers.BooleanField(default=True)
    system_notifications = serializers.BooleanField(default=True)
    achievement_notifications = serializers.BooleanField(default=True)
    
    push_notifications = serializers.BooleanField(default=True)
    sms_notifications = serializers.BooleanField(default=False)
    email_notifications = serializers.BooleanField(default=False)
    
    quiet_hours_enabled = serializers.BooleanField(default=False)
    quiet_hours_start = serializers.TimeField(required=False, allow_null=True)
    quiet_hours_end = serializers.TimeField(required=False, allow_null=True)
    
    def validate(self, attrs):
        if attrs.get('quiet_hours_enabled'):
            if not attrs.get('quiet_hours_start') or not attrs.get('quiet_hours_end'):
                raise serializers.ValidationError(
                    "Both quiet_hours_start and quiet_hours_end are required when quiet hours are enabled"
                )
        
        return attrs


class NotificationFilterSerializer(serializers.Serializer):
    """Serializer for notification filtering"""
    notification_type = serializers.ChoiceField(
        choices=Notification.NotificationTypeChoices.choices,
        required=False
    )
    channel = serializers.ChoiceField(
        choices=Notification.ChannelChoices.choices,
        required=False
    )
    is_read = serializers.BooleanField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    
    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date cannot be after end_date")
        
        return attrs


class FCMTokenSerializer(serializers.Serializer):
    """Serializer for FCM token registration"""
    token = serializers.CharField(max_length=500)
    device_type = serializers.ChoiceField(choices=[
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web')
    ])
    
    def validate_token(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Invalid FCM token")
        return value.strip()


class NotificationAnalyticsSerializer(serializers.Serializer):
    """Serializer for notification analytics"""
    period = serializers.DictField()
    total_sent = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    read_rate = serializers.FloatField()
    
    # Channel breakdown
    channel_stats = serializers.DictField()
    
    # Type breakdown
    type_stats = serializers.DictField()
    
    # Daily breakdown
    daily_breakdown = serializers.ListField()
    
    # Top performing notifications
    top_notifications = serializers.ListField()
    
    # Failed notifications
    failed_notifications = serializers.IntegerField()
    failure_rate = serializers.FloatField()


# Response Serializers for Swagger Documentation

class NotificationListResponseSerializer(BaseResponseSerializer):
    """Response serializer for notification list endpoint"""
    class NotificationListDataSerializer(serializers.Serializer):
        notifications = NotificationListSerializer(many=True)
        pagination = serializers.DictField()
    
    data = NotificationListDataSerializer()


class NotificationDetailResponseSerializer(BaseResponseSerializer):
    """Response serializer for notification detail endpoint"""
    data = NotificationDetailSerializer()


class NotificationStatsResponseSerializer(BaseResponseSerializer):
    """Response serializer for notification stats endpoint"""
    data = NotificationStatsSerializer()


class NotificationMarkAllReadResponseSerializer(BaseResponseSerializer):
    """Response serializer for mark all read endpoint"""
    class MarkAllReadDataSerializer(serializers.Serializer):
        message = serializers.CharField()
        updated_count = serializers.IntegerField()
    
    data = MarkAllReadDataSerializer()


class NotificationTemplateResponseSerializer(BaseResponseSerializer):
    """Response serializer for notification template endpoint"""
    data = NotificationTemplateSerializer(many=True)


class NotificationAnalyticsResponseSerializer(BaseResponseSerializer):
    """Response serializer for notification analytics endpoint"""
    data = NotificationAnalyticsSerializer()
