from __future__ import annotations

from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from typing import Dict, Any

from api.common.tasks.base import BaseTask
from api.user.rentals.models import Rental, RentalPackage


@shared_task(base=BaseTask, bind=True)
def check_overdue_rentals(self):
    """Check for overdue rentals and update their status"""
    try:
        now = timezone.now()
        
        # Find active rentals that are past due
        overdue_rentals = Rental.objects.filter(
            status='ACTIVE',
            due_at__lt=now
        )
        
        updated_count = 0
        
        for rental in overdue_rentals:
            # Update status to overdue
            rental.status = 'OVERDUE'
            rental.save(update_fields=['status', 'updated_at'])
            updated_count += 1
            
            # Send overdue notification
            from api.user.notifications.services import notify
            
            overdue_hours = int((now - rental.due_at).total_seconds() / 3600)
            penalty_amount = float(rental.overdue_amount)
            
            # Send rental overdue notification using clean API
            notify(rental.user, 'rental_overdue',
                  async_send=True,
                  powerbank_id=rental.powerbank.serial_number,
                  overdue_hours=overdue_hours,
                  penalty_amount=penalty_amount)
        
        self.logger.info(f"Updated {updated_count} overdue rentals")
        return {'updated_count': updated_count}
        
    except Exception as e:
        self.logger.error(f"Failed to check overdue rentals: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def calculate_overdue_charges(self):
    """Calculate and apply overdue charges for late returns"""
    try:
        # Find overdue rentals that haven't been charged yet
        overdue_rentals = Rental.objects.filter(
            status='OVERDUE',
            overdue_amount=0  # Not yet charged
        )
        
        charged_count = 0
        
        for rental in overdue_rentals:
            try:
                # Calculate overdue time
                now = timezone.now()
                overdue_duration = now - rental.due_at
                overdue_minutes = int(overdue_duration.total_seconds() / 60)
                
                # Calculate overdue charges using configurable rates
                from api.common.utils.helpers import calculate_late_fee_amount, get_package_rate_per_minute
                package_rate_per_minute = get_package_rate_per_minute(rental.package)
                overdue_amount = calculate_late_fee_amount(package_rate_per_minute, overdue_minutes)
                
                # Update rental with overdue charges
                rental.overdue_amount = overdue_amount
                rental.payment_status = 'PENDING'
                rental.save(update_fields=['overdue_amount', 'payment_status', 'updated_at'])
                
                charged_count += 1
                
                # Send overdue charges notification using clean API
                from api.user.notifications.services import notify
                notify(
                    rental.user,
                    'fines_dues',
                    async_send=True,
                    amount=float(overdue_amount),
                    reason=f"Overdue charges for rental {rental.rental_code}"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to calculate charges for rental {rental.id}: {str(e)}")
        
        self.logger.info(f"Calculated overdue charges for {charged_count} rentals")
        return {'charged_count': charged_count}
        
    except Exception as e:
        self.logger.error(f"Failed to calculate overdue charges: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def auto_complete_abandoned_rentals(self):
    """Auto-complete rentals that have been overdue for too long"""
    try:
        # Find rentals overdue for more than 24 hours
        cutoff_time = timezone.now() - timezone.timedelta(hours=24)
        
        abandoned_rentals = Rental.objects.filter(
            status='OVERDUE',
            due_at__lt=cutoff_time
        )
        
        completed_count = 0
        
        for rental in abandoned_rentals:
            try:
                # Mark as completed (assumed lost/stolen)
                rental.status = 'COMPLETED'
                rental.ended_at = timezone.now()
                rental.is_returned_on_time = False
                
                # Calculate final charges (including penalty for lost power bank)
                lost_penalty = 5000  # NPR 5000 penalty for lost power bank
                rental.overdue_amount += lost_penalty
                
                rental.rental_metadata['auto_completed'] = True
                rental.rental_metadata['lost_penalty'] = lost_penalty
                rental.rental_metadata['completion_reason'] = 'abandoned'
                
                rental.save(update_fields=[
                    'status', 'ended_at', 'is_returned_on_time', 
                    'overdue_amount', 'rental_metadata', 'updated_at'
                ])
                
                # Mark power bank as lost
                if rental.power_bank:
                    rental.power_bank.status = 'DAMAGED'  # Or create a 'LOST' status
                    rental.power_bank.hardware_info['lost_date'] = timezone.now().isoformat()
                    rental.power_bank.save(update_fields=['status', 'hardware_info'])
                
                # Release slot
                if rental.slot:
                    rental.slot.status = 'AVAILABLE'
                    rental.slot.current_rental = None
                    rental.slot.save(update_fields=['status', 'current_rental'])
                
                completed_count += 1
                
                # Send notification about completion and charges
                from api.user.notifications.services import notify
                
                # Send rental auto-completion notification using clean API
                notify(rental.user, 'rental_auto_completed',
                      async_send=True,
                      powerbank_id=rental.power_bank.serial_number,
                      total_cost=float(rental.overdue_amount))
                
            except Exception as e:
                self.logger.error(f"Failed to auto-complete rental {rental.id}: {str(e)}")
        
        self.logger.info(f"Auto-completed {completed_count} abandoned rentals")
        return {'completed_count': completed_count}
        
    except Exception as e:
        self.logger.error(f"Failed to auto-complete abandoned rentals: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def send_rental_reminders(self):
    """Send reminders for rentals approaching due time"""
    try:
        # Send reminders 15 minutes before due time
        reminder_time = timezone.now() + timezone.timedelta(minutes=15)
        
        upcoming_due_rentals = Rental.objects.filter(
            status='ACTIVE',
            due_at__lte=reminder_time,
            due_at__gt=timezone.now()
        )
        
        # Filter out rentals that already received reminders
        rentals_to_remind = []
        for rental in upcoming_due_rentals:
            if not rental.rental_metadata.get('reminder_sent'):
                rentals_to_remind.append(rental)
        
        reminder_count = 0
        
        for rental in rentals_to_remind:
            try:
                # Send reminder notification
                from api.user.notifications.tasks import send_notification_task
                send_notification_task.delay(
                    str(rental.user.id),
                    'rental_reminder',
                    {
                        'rental_id': str(rental.id),
                        'rental_code': rental.rental_code,
                        'due_time': rental.due_at.strftime('%H:%M')
                    }
                )
                
                # Mark reminder as sent
                rental.rental_metadata['reminder_sent'] = True
                rental.rental_metadata['reminder_sent_at'] = timezone.now().isoformat()
                rental.save(update_fields=['rental_metadata'])
                
                reminder_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to send reminder for rental {rental.id}: {str(e)}")
        
        self.logger.info(f"Sent {reminder_count} rental reminders")
        return {'reminder_count': reminder_count}
        
    except Exception as e:
        self.logger.error(f"Failed to send rental reminders: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def cleanup_old_rental_data(self):
    """Clean up old rental data"""
    try:
        # Clean up old completed rentals (older than 2 years)
        two_years_ago = timezone.now() - timezone.timedelta(days=730)
        
        old_rentals = Rental.objects.filter(
            status='COMPLETED',
            ended_at__lt=two_years_ago,
            payment_status='PAID'  # Only clean up fully paid rentals
        )
        
        # Clean up related data first
        from api.user.rentals.models import RentalLocation, RentalExtension, RentalIssue
        
        old_rental_ids = list(old_rentals.values_list('id', flat=True))
        
        deleted_locations = RentalLocation.objects.filter(
            rental_id__in=old_rental_ids
        ).delete()[0]
        
        deleted_extensions = RentalExtension.objects.filter(
            rental_id__in=old_rental_ids
        ).delete()[0]
        
        # Keep rental issues for audit purposes, just clean locations and extensions
        
        # Don't delete the rental records themselves, just clean up related data
        # deleted_rentals = old_rentals.delete()[0]
        
        self.logger.info(f"Cleaned up {deleted_locations} locations and {deleted_extensions} extensions")
        return {
            'deleted_locations': deleted_locations,
            'deleted_extensions': deleted_extensions,
            # 'deleted_rentals': deleted_rentals
        }
        
    except Exception as e:
        self.logger.error(f"Failed to cleanup old rental data: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def generate_rental_analytics_report(self, date_range: tuple = None):
    """Generate comprehensive rental analytics report"""
    try:
        from api.user.rentals.services import RentalAnalyticsService
        
        service = RentalAnalyticsService()
        
        if date_range:
            from datetime import datetime
            start_date = datetime.fromisoformat(date_range[0])
            end_date = datetime.fromisoformat(date_range[1])
            date_range = (start_date, end_date)
        
        analytics = service.get_rental_analytics(date_range)
        
        # Cache the analytics report
        from django.core.cache import cache
        if date_range:
            cache_key = f"rental_analytics:{date_range[0].date()}:{date_range[1].date()}"
        else:
            cache_key = "rental_analytics:last_30_days"
        
        cache.set(cache_key, analytics, timeout=3600)  # 1 hour
        
        self.logger.info("Rental analytics report generated")
        return analytics
        
    except Exception as e:
        self.logger.error(f"Failed to generate rental analytics: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def update_rental_package_popularity(self):
    """Update popularity scores for rental packages"""
    try:
        # Calculate popularity based on last 30 days usage
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        
        packages = RentalPackage.objects.filter(is_active=True)
        updated_count = 0
        
        for package in packages:
            rental_count = Rental.objects.filter(
                package=package,
                created_at__gte=thirty_days_ago
            ).count()
            
            # Simple popularity score (can be made more sophisticated)
            popularity_score = min(rental_count * 10, 1000)  # Max score of 1000
            
            # Store in package metadata
            package.package_metadata['popularity_score'] = popularity_score
            package.package_metadata['last_updated'] = timezone.now().isoformat()
            package.save(update_fields=['package_metadata'])
            
            updated_count += 1
        
        self.logger.info(f"Updated popularity scores for {updated_count} packages")
        return {'updated_packages': updated_count}
        
    except Exception as e:
        self.logger.error(f"Failed to update package popularity: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def sync_rental_payment_status(self):
    """Sync rental payment status with actual payments"""
    try:
        # Find rentals with pending payment status
        pending_rentals = Rental.objects.filter(
            payment_status='PENDING',
            status__in=['COMPLETED', 'OVERDUE']
        )
        
        synced_count = 0
        
        for rental in pending_rentals:
            try:
                # Check if payment has been made
                from api.user.payments.models import Transaction
                
                payment_exists = Transaction.objects.filter(
                    user=rental.user,
                    related_rental=rental,
                    status='SUCCESS',
                    transaction_type__in=['RENTAL', 'RENTAL_DUE']
                ).exists()
                
                if payment_exists:
                    rental.payment_status = 'PAID'
                    rental.save(update_fields=['payment_status', 'updated_at'])
                    synced_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to sync payment status for rental {rental.id}: {str(e)}")
        
        self.logger.info(f"Synced payment status for {synced_count} rentals")
        return {'synced_count': synced_count}
        
    except Exception as e:
        self.logger.error(f"Failed to sync rental payment status: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def detect_rental_anomalies(self):
    """Detect anomalies in rental patterns"""
    try:
        anomalies = []
        
        # Check for unusually long active rentals (more than 48 hours)
        forty_eight_hours_ago = timezone.now() - timezone.timedelta(hours=48)
        
        long_rentals = Rental.objects.filter(
            status='ACTIVE',
            started_at__lt=forty_eight_hours_ago
        )
        
        for rental in long_rentals:
            anomalies.append({
                'type': 'long_active_rental',
                'rental_id': str(rental.id),
                'rental_code': rental.rental_code,
                'user_id': str(rental.user.id),
                'duration_hours': int((timezone.now() - rental.started_at).total_seconds() / 3600),
                'severity': 'high'
            })
        
        # Check for users with multiple active rentals (should not happen)
        from django.db.models import Count
        
        users_with_multiple_rentals = Rental.objects.filter(
            status__in=['ACTIVE', 'PENDING']
        ).values('user').annotate(
            rental_count=Count('id')
        ).filter(rental_count__gt=1)
        
        for user_data in users_with_multiple_rentals:
            anomalies.append({
                'type': 'multiple_active_rentals',
                'user_id': str(user_data['user']),
                'rental_count': user_data['rental_count'],
                'severity': 'critical'
            })
        
        # Check for rentals without power banks assigned
        rentals_without_powerbank = Rental.objects.filter(
            status='ACTIVE',
            power_bank__isnull=True
        )
        
        for rental in rentals_without_powerbank:
            anomalies.append({
                'type': 'rental_without_powerbank',
                'rental_id': str(rental.id),
                'rental_code': rental.rental_code,
                'severity': 'high'
            })
        
        # Send alert if anomalies found
        if anomalies:
            from api.user.notifications.services import notify_bulk
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            
            # Send bulk notification to all admins
            notify_bulk(
                admin_users,
                'rental_anomalies_alert',
                async_send=True,
                anomaly_count=len(anomalies),
                anomalies=anomalies
            )
        
        self.logger.info(f"Detected {len(anomalies)} rental anomalies")
        return {
            'anomaly_count': len(anomalies),
            'anomalies': anomalies
        }
        
    except Exception as e:
        self.logger.error(f"Failed to detect rental anomalies: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def resume_rental_start_from_intent(self, intent_id: str):
    """Resume rental start after successful top-up verification."""
    try:
        from api.user.payments.repositories import PaymentIntentRepository
        from api.user.rentals.services import RentalService

        intent = PaymentIntentRepository.get_by_intent_id(intent_id)
        if not intent:
            self.logger.warning(f"Payment intent not found: {intent_id}")
            return {'status': 'NOT_FOUND'}

        metadata = intent.intent_metadata or {}
        if metadata.get('flow') != 'RENTAL_START':
            return {'status': 'SKIPPED'}

        if intent.status != 'COMPLETED':
            return {'status': 'NOT_READY'}

        if metadata.get('rental_id'):
            return {'status': 'ALREADY_STARTED', 'rental_id': metadata.get('rental_id')}

        metadata['rental_start_status'] = 'PROCESSING'
        intent.intent_metadata = metadata
        intent.save(update_fields=['intent_metadata'])

        pricing_override = None
        if metadata.get('actual_price') is not None:
            pricing_override = {
                'actual_price': metadata.get('actual_price'),
                'discount_id': metadata.get('discount_id'),
                'discount_amount': metadata.get('discount_amount'),
                'discount_metadata': metadata.get('discount_metadata')
            }

        payment_mode = metadata.get('payment_mode') or metadata.get('payment_mode_requested') or 'wallet_points'
        wallet_amount = metadata.get('wallet_amount')
        points_to_use = metadata.get('points_to_use')
        if points_to_use is not None:
            try:
                points_to_use = int(points_to_use)
            except (TypeError, ValueError):
                points_to_use = None

        service = RentalService()
        rental = service.start_rental(
            user=intent.user,
            station_sn=metadata.get('station_sn'),
            package_id=metadata.get('package_id'),
            powerbank_sn=metadata.get('powerbank_sn'),
            pricing_override=pricing_override,
            payment_mode=payment_mode,
            wallet_amount=wallet_amount,
            points_to_use=points_to_use
        )

        metadata['rental_start_status'] = 'SUCCESS'
        metadata['rental_id'] = str(rental.id)
        intent.intent_metadata = metadata
        intent.save(update_fields=['intent_metadata'])

        return {'status': 'SUCCESS', 'rental_id': str(rental.id)}

    except Exception as e:
        try:
            if 'intent' in locals() and intent:
                metadata = intent.intent_metadata or {}
                metadata['rental_start_status'] = 'FAILED'
                metadata['rental_error'] = str(e)
                intent.intent_metadata = metadata
                intent.save(update_fields=['intent_metadata'])
        except Exception as update_error:
            self.logger.error(f"Failed to update intent metadata: {update_error}")

        self.logger.error(f"Failed to resume rental start for intent {intent_id}: {str(e)}")
        return {'status': 'FAILED', 'error': str(e)}
