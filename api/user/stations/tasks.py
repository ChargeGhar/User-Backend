from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from api.common.tasks.base import BaseTask
from api.user.stations.models import PowerBank, Station, StationSlot

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="stations"
)
def verify_popup_completion(self, rental_id: str, station_sn: str, expected_powerbank_sn: str = None):
    """
    Verify popup completed after sync timeout
    
    Called when sync popup times out but rental was created.
    Checks device logs for successful popup within last 2 minutes.
    
    Args:
        rental_id: Rental ID to update
        station_sn: Station serial number
        expected_powerbank_sn: Expected powerbank SN (optional for random popup)
    """
    from api.user.rentals.models import Rental
    from api.user.stations.services.device_api_service import DeviceAPIService
    
    try:
        rental = Rental.objects.get(id=rental_id)
        
        # Skip if already completed or cancelled
        if rental.status not in ['PENDING', 'PENDING_POPUP']:
            logger.info(f"Rental {rental_id} already processed, status={rental.status}")
            return {"status": "skipped", "reason": f"rental status is {rental.status}"}
        
        device_service = DeviceAPIService()
        recent_popups = device_service.get_recent_popups(station_sn, limit=20)
        
        # Check if our powerbank was popped in last 2 minutes
        cutoff = int((timezone.now().timestamp() - 120) * 1000)  # Convert to milliseconds
        
        for popup in recent_popups:
            if popup.timestamp > cutoff:
                parsed = popup.parsed
                popup_sn = parsed.get("powerbankSN", "")
                popup_status = parsed.get("status", 0)
                
                # If we have expected SN, match it; otherwise accept any successful popup
                if popup_status == 1:
                    if expected_powerbank_sn is None or popup_sn == expected_powerbank_sn:
                        # Found successful popup!
                        logger.info(
                            f"Verified popup for rental {rental_id}: "
                            f"powerbank={popup_sn}"
                        )
                        rental.status = 'ACTIVE'
                        rental.started_at = timezone.now()
                        rental.rental_metadata['popup_verified'] = True
                        rental.rental_metadata['popup_verified_at'] = timezone.now().isoformat()
                        rental.rental_metadata['verified_powerbank_sn'] = popup_sn
                        rental.save(update_fields=['status', 'started_at', 'rental_metadata'])
                        
                        return {"status": "verified", "powerbank_sn": popup_sn}
        
        # Not found - retry or mark failed
        if self.request.retries < self.max_retries:
            logger.warning(f"Popup not verified for rental {rental_id}, retrying... (attempt {self.request.retries + 1})")
            raise self.retry()
        else:
            logger.error(f"Popup verification failed for rental {rental_id} after {self.max_retries} retries")
            rental.status = 'CANCELLED'
            rental.rental_metadata['popup_failed'] = True
            rental.rental_metadata['popup_failed_at'] = timezone.now().isoformat()
            rental.save(update_fields=['status', 'rental_metadata'])
            
            # TODO: Trigger refund if prepaid
            # For now, just notify user
            try:
                from api.user.notifications.services import notify
                notify(
                    rental.user,
                    'rental_popup_failed',
                    async_send=True,
                    rental_code=rental.rental_code,
                    station_name=rental.station.station_name
                )
            except Exception as notify_error:
                logger.error(f"Failed to send popup failure notification: {notify_error}")
            
            return {"status": "failed", "reason": "popup not verified after retries"}
            
    except Rental.DoesNotExist:
        logger.error(f"Rental {rental_id} not found")
        return {"status": "error", "reason": "rental not found"}
    except Exception as e:
        logger.error(f"Verify popup error: rental={rental_id}, error={e}")
        raise self.retry(exc=e)


@shared_task(base=BaseTask, bind=True)
def check_offline_stations(self):
    """
    Check for stations that haven't sent heartbeat recently.

    SCHEDULED: Runs every 5 minutes via Celery Beat.
    Marks stations as offline if no heartbeat for 10 minutes.

    Returns:
        dict: Number of stations marked offline
    """
    try:
        # Consider stations offline if no heartbeat for 10 minutes
        cutoff_time = timezone.now() - timezone.timedelta(minutes=10)

        offline_stations = Station.objects.filter(
            Q(last_heartbeat__lt=cutoff_time) | Q(last_heartbeat__isnull=True),
            status="ONLINE",
        )

        updated_count = offline_stations.update(status="OFFLINE")

        self.logger.info(f"Marked {updated_count} stations as offline")
        return {"offline_count": updated_count}

    except Exception as e:
        self.logger.error(f"Failed to check offline stations: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def optimize_power_bank_distribution(self):
    """
    Optimize power bank distribution across stations.

    SCHEDULED: Runs daily via Celery Beat.
    Identifies stations with low availability and suggests redistribution.

    Returns:
        dict: Stations needing redistribution
    """
    try:
        # Get stations with low power bank availability
        low_availability_stations = (
            Station.objects.annotate(
                available_count=Count("slots", filter=Q(slots__status="AVAILABLE"))
            )
            .filter(
                status="ONLINE",
                is_maintenance=False,
                available_count__lt=2,  # Less than 2 available slots
            )
            .values("id", "name", "location", "available_count")
        )

        # Get stations with high availability (potential donors)
        high_availability_stations = (
            Station.objects.annotate(
                available_count=Count("slots", filter=Q(slots__status="AVAILABLE"))
            )
            .filter(
                status="ONLINE",
                is_maintenance=False,
                available_count__gt=5,  # More than 5 available slots
            )
            .values("id", "name", "location", "available_count")
        )

        low_list = list(low_availability_stations)
        high_list = list(high_availability_stations)

        # Log recommendations
        if low_list:
            self.logger.warning(
                f"Found {len(low_list)} stations with low availability: "
                f"{[s['name'] for s in low_list]}"
            )

        if high_list:
            self.logger.info(
                f"Found {len(high_list)} stations with high availability for redistribution"
            )

        # Send notification to admin if action needed
        if low_list and high_list:
            try:
                from api.user.notifications.services import notify

                admin_users = User.objects.filter(is_staff=True, is_active=True)
                for admin in admin_users:
                    notify(
                        admin,
                        "power_bank_redistribution_needed",
                        async_send=True,
                        low_stations_count=len(low_list),
                        high_stations_count=len(high_list),
                    )
            except Exception as e:
                self.logger.error(f"Failed to send redistribution notification: {e}")

        return {
            "low_availability_stations": low_list,
            "high_availability_stations": high_list,
            "action_needed": len(low_list) > 0 and len(high_list) > 0,
        }

    except Exception as e:
        self.logger.error(f"Failed to optimize power bank distribution: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def update_station_popularity_score(self):
    """
    Update popularity scores for stations based on usage.

    SCHEDULED: Runs daily via Celery Beat.
    Calculates popularity based on rental activity in last 30 days.

    Returns:
        dict: Number of stations updated
    """
    try:
        from api.user.rentals.models import Rental

        # Calculate popularity based on last 30 days rentals
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

        stations = Station.objects.all()
        updated_count = 0

        for station in stations:
            # Count rentals from this station
            pickup_count = Rental.objects.filter(
                pickup_station=station, created_at__gte=thirty_days_ago
            ).count()

            return_count = Rental.objects.filter(
                return_station=station, returned_at__gte=thirty_days_ago
            ).count()

            # Calculate popularity score (weighted: pickups 60%, returns 40%)
            popularity_score = (pickup_count * 0.6) + (return_count * 0.4)

            # Update station metadata
            if station.metadata is None:
                station.metadata = {}

            station.metadata["popularity_score"] = round(popularity_score, 2)
            station.metadata["pickup_count_30d"] = pickup_count
            station.metadata["return_count_30d"] = return_count
            station.metadata["last_popularity_update"] = timezone.now().isoformat()

            station.save(update_fields=["metadata", "updated_at"])
            updated_count += 1

        self.logger.info(f"Updated popularity scores for {updated_count} stations")
        return {"updated_count": updated_count}

    except Exception as e:
        self.logger.error(f"Failed to update station popularity: {str(e)}")
        raise
