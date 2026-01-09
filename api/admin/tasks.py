from __future__ import annotations

from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from typing import Dict, Any

from api.common.tasks.base import BaseTask, AnalyticsTask
from api.admin.models import AdminActionLog, SystemLog


@shared_task(base=AnalyticsTask, bind=True)
def generate_admin_dashboard_report(self):
    """Generate comprehensive admin dashboard analytics"""
    try:
        from api.admin.services import AdminAnalyticsService

        service = AdminAnalyticsService()
        analytics = service.get_dashboard_analytics()

        # Cache the dashboard data
        from django.core.cache import cache

        cache.set("admin_dashboard_analytics", analytics, timeout=300)  # 5 minutes

        self.logger.info("Admin dashboard analytics generated")
        return analytics

    except Exception as e:
        self.logger.error(f"Failed to generate admin dashboard report: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def cleanup_old_admin_logs(self):
    """Clean up old admin action logs (older than 1 year)"""
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=365)

        deleted_count = AdminActionLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]

        self.logger.info(f"Cleaned up {deleted_count} old admin action logs")
        return {"deleted_count": deleted_count}

    except Exception as e:
        self.logger.error(f"Failed to cleanup admin logs: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def cleanup_old_system_logs(self):
    """Clean up old system logs (older than 3 months)"""
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=90)

        # Keep ERROR and CRITICAL logs longer (6 months)
        error_cutoff = timezone.now() - timezone.timedelta(days=180)

        # Delete old non-critical logs
        deleted_normal = SystemLog.objects.filter(
            created_at__lt=cutoff_date, level__in=["DEBUG", "INFO", "WARNING"]
        ).delete()[0]

        # Delete old critical logs
        deleted_critical = SystemLog.objects.filter(
            created_at__lt=error_cutoff, level__in=["ERROR", "CRITICAL"]
        ).delete()[0]

        total_deleted = deleted_normal + deleted_critical

        self.logger.info(f"Cleaned up {total_deleted} old system logs")
        return {
            "deleted_normal": deleted_normal,
            "deleted_critical": deleted_critical,
            "total_deleted": total_deleted,
        }

    except Exception as e:
        self.logger.error(f"Failed to cleanup system logs: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def monitor_system_health(self):
    """Monitor system health and alert on issues"""
    try:
        from api.admin.services import AdminSystemService

        service = AdminSystemService()
        health_data = service.get_system_health()

        # Check for critical issues
        alerts = []

        # Check error rate
        if health_data.get("error_rate", 0) > 0.05:  # 5% error rate threshold
            alerts.append(
                {
                    "type": "HIGH_ERROR_RATE",
                    "message": f"Error rate is {health_data['error_rate']:.2%}",
                    "severity": "high",
                }
            )

        # Check response time
        if health_data.get("response_time_avg", 0) > 1000:  # 1 second threshold
            alerts.append(
                {
                    "type": "SLOW_RESPONSE",
                    "message": f"Average response time is {health_data['response_time_avg']:.1f}ms",
                    "severity": "medium",
                }
            )

        # Check resource usage
        if health_data.get("cpu_usage", 0) > 80:
            alerts.append(
                {
                    "type": "HIGH_CPU_USAGE",
                    "message": f"CPU usage is {health_data['cpu_usage']:.1f}%",
                    "severity": "high",
                }
            )

        if health_data.get("memory_usage", 0) > 85:
            alerts.append(
                {
                    "type": "HIGH_MEMORY_USAGE",
                    "message": f"Memory usage is {health_data['memory_usage']:.1f}%",
                    "severity": "high",
                }
            )

        # Check failed tasks
        if health_data.get("failed_tasks", 0) > 10:
            alerts.append(
                {
                    "type": "HIGH_FAILED_TASKS",
                    "message": f"{health_data['failed_tasks']} tasks have failed",
                    "severity": "medium",
                }
            )

        # Send alerts if any issues found
        if alerts:
            from api.user.notifications.services import notify_bulk
            from django.contrib.auth import get_user_model

            User = get_user_model()
            admin_users = User.objects.filter(is_staff=True, is_active=True)

            # Send bulk notification to all admins
            notify_bulk(
                admin_users,
                "system_health_alert",
                async_send=True,
                alert_count=len(alerts),
                alerts=alerts,
            )

        # Log system health
        SystemLog.objects.create(
            level="INFO",
            module="system_monitor",
            message=f"System health check completed. {len(alerts)} alerts generated.",
            context={"health_data": health_data, "alerts": alerts},
        )

        self.logger.info(f"System health monitored. {len(alerts)} alerts generated")
        return {"health_data": health_data, "alerts": alerts, "alert_count": len(alerts)}

    except Exception as e:
        self.logger.error(f"Failed to monitor system health: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def generate_revenue_report(self, date_range: tuple = None):
    """Generate detailed revenue report"""
    try:
        if date_range:
            from datetime import datetime

            start_date = datetime.fromisoformat(date_range[0])
            end_date = datetime.fromisoformat(date_range[1])
        else:
            # Default to current month
            end_date = timezone.now()
            start_date = end_date.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )

        from api.user.payments.models import Transaction
        from api.user.rentals.models import Rental

        # Get successful transactions in date range
        transactions = Transaction.objects.filter(
            status="SUCCESS", created_at__range=(start_date, end_date)
        )

        # Revenue by transaction type
        revenue_by_type = (
            transactions.values("transaction_type")
            .annotate(total_revenue=Sum("amount"), transaction_count=Count("id"))
            .order_by("-total_revenue")
        )

        # Revenue by payment method
        revenue_by_method = (
            transactions.values("payment_method_type")
            .annotate(total_revenue=Sum("amount"), transaction_count=Count("id"))
            .order_by("-total_revenue")
        )

        # Daily revenue breakdown
        daily_revenue = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            day_revenue = (
                transactions.filter(created_at__date=current_date).aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )

            daily_revenue.append(
                {"date": current_date.isoformat(), "revenue": float(day_revenue)}
            )

            current_date += timezone.timedelta(days=1)

        # Top revenue generating stations
        top_stations = (
            Rental.objects.filter(
                created_at__range=(start_date, end_date), payment_status="PAID"
            )
            .values("station__station_name")
            .annotate(total_revenue=Sum("amount_paid"), rental_count=Count("id"))
            .order_by("-total_revenue")[:10]
        )

        total_revenue = transactions.aggregate(total=Sum("amount"))["total"] or 0

        report = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "total_revenue": float(total_revenue),
            "total_transactions": transactions.count(),
            "average_transaction_value": float(total_revenue / transactions.count())
            if transactions.count() > 0
            else 0,
            "revenue_by_type": list(revenue_by_type),
            "revenue_by_method": list(revenue_by_method),
            "daily_revenue": daily_revenue,
            "top_stations": list(top_stations),
        }

        # Cache the report
        from django.core.cache import cache

        cache_key = f"revenue_report:{start_date.date()}:{end_date.date()}"
        cache.set(cache_key, report, timeout=3600)  # 1 hour

        self.logger.info(
            f"Revenue report generated for {start_date.date()} to {end_date.date()}"
        )
        return report

    except Exception as e:
        self.logger.error(f"Failed to generate revenue report: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def backup_critical_data(self):
    """Backup critical system data"""
    try:
        from django.core.management import call_command
        import os
        from django.conf import settings

        # Generate backup filename with timestamp
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.json"

        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        backup_path = os.path.join(backup_dir, backup_filename)

        # Create database backup using Django's dumpdata
        with open(backup_path, "w") as backup_file:
            call_command(
                "dumpdata",
                "--natural-foreign",
                "--natural-primary",
                "--exclude=contenttypes",
                "--exclude=auth.permission",
                "--exclude=sessions",
                stdout=backup_file,
            )

        # Log backup creation
        SystemLog.objects.create(
            level="INFO",
            module="backup_system",
            message=f"Database backup created: {backup_filename}",
            context={
                "backup_path": backup_path,
                "backup_size": os.path.getsize(backup_path),
            },
        )

        # Clean up old backups (keep last 7 days)
        cutoff_date = timezone.now() - timezone.timedelta(days=7)

        for filename in os.listdir(backup_dir):
            if filename.startswith("backup_") and filename.endswith(".json"):
                file_path = os.path.join(backup_dir, filename)
                file_time = timezone.datetime.fromtimestamp(
                    os.path.getctime(file_path), tz=timezone.get_current_timezone()
                )

                if file_time < cutoff_date:
                    os.remove(file_path)

        self.logger.info(f"Database backup created: {backup_filename}")
        return {
            "backup_filename": backup_filename,
            "backup_path": backup_path,
            "backup_size": os.path.getsize(backup_path),
        }

    except Exception as e:
        self.logger.error(f"Failed to backup critical data: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def send_admin_digest_report(self):
    """Send daily digest report to admin users"""
    try:
        from api.admin.services import AdminAnalyticsService

        # Generate analytics
        analytics_service = AdminAnalyticsService()
        analytics = analytics_service.get_dashboard_analytics()

        # Prepare digest message
        digest_message = f"""
Daily System Digest:

👥 Users: {analytics["total_users"]} total, {analytics["new_users_today"]} new today
🔋 Rentals: {analytics["active_rentals"]} active, {analytics["completed_rentals_today"]} completed today
💰 Revenue: NPR {analytics["revenue_today"]:,.2f} today, NPR {analytics["revenue_this_month"]:,.2f} this month
🏢 Stations: {analytics["online_stations"]}/{analytics["total_stations"]} online
⚠️ Issues: {len(analytics["recent_issues"])} recent issues

System Status: All systems operational
        """.strip()

        # Send to admin users
        from django.contrib.auth import get_user_model
        from api.user.notifications.services import notify_bulk

        User = get_user_model()
        admin_users = User.objects.filter(is_staff=True, is_active=True)

        # Send bulk notification to all admins
        notify_bulk(
            admin_users,
            "daily_system_digest",
            async_send=True,
            analytics=analytics,
            digest_message=digest_message,
        )

        self.logger.info(f"Daily digest sent to {admin_users.count()} admin users")
        return {"admins_notified": admin_users.count(), "analytics": analytics}

    except Exception as e:
        self.logger.error(f"Failed to send admin digest report: {str(e)}")
        raise
