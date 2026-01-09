from __future__ import annotations

import os

from celery import Celery

# Set up Django before any imports that might use Django models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.config.settings")

import django
django.setup()

from api.config import celery as config

app = Celery("main")
app.config_from_object(config)

# Auto-discover tasks from all apps
app.autodiscover_tasks(
    [
        "api.user.auth",
        "api.user.stations",
        "api.user.payments",
        "api.user.points",
        "api.user.notifications",
        "api.user.rentals",
        "api.admin",
        "api.user.content",
        "api.user.social",
        "api.user.promotions",
        "api.user.system",
    ]
)

# Configure task routes for better organization
app.conf.task_routes = {
    # User-related tasks
    "api.user.auth.tasks.*": {"queue": "users"},
    # Station-related tasks
    "api.user.stations.tasks.*": {"queue": "stations"},
    # Payment-related tasks (high priority)
    "api.user.payments.tasks.*": {"queue": "payments"},
    # Points and referral tasks
    "api.user.points.tasks.*": {"queue": "points"},
    # Notification tasks (high priority)
    "api.user.notifications.tasks.*": {"queue": "notifications"},
    # Rental tasks (critical)
    "api.user.rentals.tasks.*": {"queue": "rentals"},
    # Admin and analytics tasks
    "api.admin.tasks.*": {"queue": "admin"},
    # System tasks (app updates, health checks)
    "api.user.system.tasks.*": {"queue": "system"},
    # Low priority tasks
    "api.user.content.tasks.*": {"queue": "low_priority"},
    "api.user.social.tasks.*": {"queue": "low_priority"},
    "api.user.promotions.tasks.*": {"queue": "low_priority"},
}

# Configure periodic tasks
app.conf.beat_schedule = {
    # Critical system tasks (every minute)
    "check-overdue-rentals": {
        "task": "api.user.rentals.tasks.check_overdue_rentals",
        "schedule": 60.0,  # Every 1 minute (increased frequency for real-time updates)
    },
    "check-offline-stations": {
        "task": "api.user.stations.tasks.check_offline_stations",
        "schedule": 300.0,  # Every 5 minutes
    },
    # Important tasks (every 15 minutes)
    "send-rental-reminders": {
        "task": "api.user.rentals.tasks.send_rental_reminders",
        "schedule": 900.0,  # Every 15 minutes
    },
    "expire-payment-intents": {
        "task": "api.user.payments.tasks.expire_payment_intents",
        "schedule": 900.0,  # Every 15 minutes
    },
    # Regular tasks (hourly)
    "calculate-overdue-charges": {
        "task": "api.user.rentals.tasks.calculate_overdue_charges",
        "schedule": 3600.0,  # Every hour
    },
    "expire-old-referrals": {
        "task": "api.user.points.tasks.expire_old_referrals",
        "schedule": 3600.0,  # Every hour
    },
    # Daily tasks
    "cleanup-old-notifications": {
        "task": "api.user.notifications.tasks.cleanup_old_notifications_task",
        "schedule": 86400.0,  # Daily
    },
    "cleanup-old-audit-logs": {
        "task": "api.user.auth.tasks.cleanup_expired_audit_logs",
        "schedule": 86400.0,  # Daily
    },
    "auto-complete-abandoned-rentals": {
        "task": "api.user.rentals.tasks.auto_complete_abandoned_rentals",
        "schedule": 86400.0,  # Daily
    },
    "detect-rental-anomalies": {
        "task": "api.user.rentals.tasks.detect_rental_anomalies",
        "schedule": 86400.0,  # Daily
    },
    "deactivate-inactive-users": {
        "task": "api.user.auth.tasks.deactivate_inactive_users",
        "schedule": 86400.0,  # Daily
    },
    "monitor-system-health": {
        "task": "api.admin.tasks.monitor_system_health",
        "schedule": 3600.0,  # Every hour
    },
    "send-admin-digest-report": {
        "task": "api.admin.tasks.send_admin_digest_report",
        "schedule": 86400.0,  # Daily at 8 AM
        "options": {"eta": "08:00"},
    },
    "backup-critical-data": {
        "task": "api.admin.tasks.backup_critical_data",
        "schedule": 86400.0,  # Daily at 1 AM
        "options": {"eta": "01:00"},
    },
    # Weekly tasks
    "cleanup-old-rental-data": {
        "task": "api.user.rentals.tasks.cleanup_old_rental_data",
        "schedule": 604800.0,  # Weekly
    },
    "cleanup-old-points-transactions": {
        "task": "api.user.points.tasks.cleanup_old_transactions",
        "schedule": 604800.0,  # Weekly
    },
    "cleanup-old-payment-data": {
        "task": "api.user.payments.tasks.cleanup_old_payment_data",
        "schedule": 604800.0,  # Weekly
    },
    "cleanup-old-admin-logs": {
        "task": "api.admin.tasks.cleanup_old_admin_logs",
        "schedule": 604800.0,  # Weekly
    },
    "cleanup-old-system-logs": {
        "task": "api.admin.tasks.cleanup_old_system_logs",
        "schedule": 259200.0,  # Every 3 days
    },
    "cleanup-old-coupon-data": {
        "task": "api.user.promotions.tasks.cleanup_old_coupon_data",
        "schedule": 604800.0,  # Weekly
    },
    "cleanup-inactive-user-achievements": {
        "task": "api.user.social.tasks.cleanup_inactive_user_achievements",
        "schedule": 604800.0,  # Weekly
    },
    # Analytics tasks (daily at 2 AM)
    "generate-rental-analytics": {
        "task": "api.user.rentals.tasks.generate_rental_analytics_report",
        "schedule": 86400.0,  # Daily
        "options": {"eta": "02:00"},
    },
    "generate-admin-dashboard-report": {
        "task": "api.admin.tasks.generate_admin_dashboard_report",
        "schedule": 1800.0,  # Every 30 minutes (reduced from 5 minutes)
    },
    "generate-revenue-report": {
        "task": "api.admin.tasks.generate_revenue_report",
        "schedule": 86400.0,  # Daily
        "options": {"eta": "04:00"},
    },
    # Maintenance tasks (weekly)
    "sync-wallet-balances": {
        "task": "api.user.payments.tasks.sync_wallet_balances",
        "schedule": 604800.0,  # Weekly
    },
    "sync-rental-payment-status": {
        "task": "api.user.rentals.tasks.sync_rental_payment_status",
        "schedule": 604800.0,  # Weekly
    },
    # Optimization tasks (daily)
    "optimize-power-bank-distribution": {
        "task": "api.user.stations.tasks.optimize_power_bank_distribution",
        "schedule": 86400.0,  # Daily
    },
    "update-station-popularity": {
        "task": "api.user.stations.tasks.update_station_popularity_score",
        "schedule": 86400.0,  # Daily
    },
    "update-package-popularity": {
        "task": "api.user.rentals.tasks.update_rental_package_popularity",
        "schedule": 86400.0,  # Daily
    },
}

# Task execution settings
app.conf.task_time_limit = 300  # 5 minutes max per task
app.conf.task_soft_time_limit = 240  # 4 minutes soft limit
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True
app.conf.worker_disable_rate_limits = False
app.conf.worker_max_tasks_per_child = 100  # Restart worker after 100 tasks to prevent memory leaks

# Connection settings for better reliability
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 10

# Error handling
app.conf.task_reject_on_worker_lost = True
# task_ignore_result is set in api/config/celery.py via environment variable
app.conf.result_expires = 3600  # 1 hour

# Monitoring (disabled to reduce memory usage)
app.conf.worker_send_task_events = False
app.conf.task_send_sent_event = False

# Memory management
app.conf.worker_max_memory_per_child = 200000  # 200MB per worker process

# Production settings (simplified)
app.conf.worker_hijack_root_logger = False  # Don't interfere with Django logging
