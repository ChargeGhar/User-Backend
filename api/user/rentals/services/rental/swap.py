"""
Rental Swap Service
===================

Handles powerbank swapping within active rentals.

Business Rules:
- User can swap only within SWAPPING_MAX_TIME window (default 5 min)
- User must return current powerbank to same station first
- Daily swap limit = available powerbanks at station
- No payment involved in swap (just exchange)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from api.common.services.base import ServiceException

if TYPE_CHECKING:
    from api.user.rentals.models import Rental
    from api.user.stations.models import Station, PowerBank


class RentalSwapMixin:
    """Mixin for rental swap operations"""
    
    @transaction.atomic
    def swap_powerbank(
        self, 
        rental_id: str, 
        user, 
        reason: str = 'OTHER',
        description: str = '',
        powerbank_sn: str = None
    ) -> 'Rental':
        """
        Swap current powerbank for a different one at same station.
        
        Rules:
        1. Must be within SWAPPING_MAX_TIME from rental start
        2. Current powerbank must be returned to station
        3. Daily swap limit per station applies
        
        Args:
            rental_id: UUID of the rental
            user: User requesting swap
            reason: Swap reason (LOW_BATTERY, DEFECTIVE, WRONG_CABLE, OTHER)
            description: Optional description
            powerbank_sn: Optional specific powerbank serial number to swap to
        
        Returns:
            Updated Rental object
        """
        from api.user.rentals.models import Rental, RentalSwap
        from api.user.stations.models import PowerBank
        
        try:
            rental = Rental.objects.select_for_update().get(id=rental_id, user=user)
            
            # Validate swap eligibility
            self._validate_swap_eligibility(rental)
            self._validate_powerbank_returned_for_swap(rental)
            self._check_swap_limit(user, rental.station)
            
            # Store old powerbank info
            old_powerbank = rental.power_bank
            old_slot = rental.slot
            old_battery = old_powerbank.battery_level if old_powerbank else 0
            
            # Get new powerbank
            new_powerbank, new_slot = self._get_swap_powerbank(
                rental.station, 
                exclude_powerbank_id=str(old_powerbank.id) if old_powerbank else None,
                requested_sn=powerbank_sn
            )
            
            # Trigger device popup for new powerbank
            from api.user.rentals.services.rental.start.device import trigger_device_popup
            
            popup_success, popup_sn = trigger_device_popup(
                rental, rental.station, new_powerbank, None
            )
            
            if not popup_success:
                raise ServiceException(
                    detail="Failed to dispense new powerbank. Please try again.",
                    code="swap_popup_failed"
                )
            
            # Update rental with new powerbank
            rental.power_bank = new_powerbank
            rental.slot = new_slot
            
            # Update metadata
            swap_info = {
                'old_powerbank_sn': old_powerbank.serial_number if old_powerbank else None,
                'new_powerbank_sn': new_powerbank.serial_number,
                'reason': reason,
                'swapped_at': timezone.now().isoformat()
            }
            
            if 'swaps' not in rental.rental_metadata:
                rental.rental_metadata['swaps'] = []
            rental.rental_metadata['swaps'].append(swap_info)
            rental.rental_metadata['total_swap_count'] = len(rental.rental_metadata['swaps'])
            
            rental.save(update_fields=['power_bank', 'slot', 'rental_metadata'])
            
            # Release old powerbank
            if old_powerbank:
                old_powerbank.status = 'AVAILABLE'
                old_powerbank.save(update_fields=['status'])
            
            if old_slot:
                old_slot.status = 'AVAILABLE'
                old_slot.current_rental = None
                old_slot.save(update_fields=['status', 'current_rental'])
            
            # Assign new powerbank
            new_powerbank.status = 'IN_USE'
            new_powerbank.save(update_fields=['status'])
            
            new_slot.status = 'OCCUPIED'
            new_slot.current_rental = rental
            new_slot.save(update_fields=['status', 'current_rental'])
            
            # Create swap log
            RentalSwap.objects.create(
                rental=rental,
                original_station=rental.station,
                old_powerbank=old_powerbank,
                old_slot=old_slot,
                old_battery_level=old_battery,
                new_powerbank=new_powerbank,
                new_slot=new_slot,
                new_battery_level=new_powerbank.battery_level,
                swap_reason=reason,
                description=description
            )
            
            # Send notification
            self._send_swap_notification(user, rental, old_powerbank, new_powerbank)
            
            self.log_info(
                f"Powerbank swapped for rental {rental.rental_code}: "
                f"{old_powerbank.serial_number if old_powerbank else 'N/A'} -> {new_powerbank.serial_number}"
            )
            
            return rental
            
        except Rental.DoesNotExist:
            raise ServiceException(detail="Rental not found", code="rental_not_found")
        except Exception as e:
            if isinstance(e, ServiceException):
                raise
            self.handle_service_error(e, "Failed to swap powerbank")
    
    def _validate_swap_eligibility(self, rental: 'Rental') -> None:
        """Check if rental is eligible for swap"""
        if rental.status != 'ACTIVE':
            raise ServiceException(
                detail="Only active rentals can swap powerbanks",
                code="invalid_rental_status"
            )
        
        if not rental.started_at:
            raise ServiceException(
                detail="Rental has not started yet",
                code="rental_not_started"
            )
        
        # Get swap window from config
        from api.user.system.services.app_config_service import AppConfigService
        config_service = AppConfigService()
        swap_window_minutes = int(config_service.get_config_cached('SWAPPING_MAX_TIME', 5))
        
        time_since_start = timezone.now() - rental.started_at
        
        if time_since_start.total_seconds() > (swap_window_minutes * 60):
            raise ServiceException(
                detail=f"Swap window expired. Swapping is only allowed within {swap_window_minutes} minutes of rental start.",
                code="swap_window_expired"
            )
    
    def _validate_powerbank_returned_for_swap(self, rental: 'Rental') -> None:
        """Verify powerbank is back in station for swap"""
        if not rental.power_bank:
            raise ServiceException(
                detail="No powerbank associated with this rental",
                code="no_powerbank"
            )
        
        # Check powerbank is back at the original station
        if rental.power_bank.current_station_id != rental.station_id:
            raise ServiceException(
                detail="Please return the powerbank to the same station before swapping.",
                code="powerbank_not_at_station"
            )
        
        if rental.power_bank.current_slot is None:
            raise ServiceException(
                detail="Please insert the powerbank into a slot before swapping.",
                code="powerbank_not_in_slot"
            )
    
    def _check_swap_limit(self, user, station: 'Station') -> None:
        """Check daily swap limit for user at station"""
        from api.user.rentals.models import RentalSwap
        from api.user.stations.models import PowerBank
        
        today = timezone.now().date()
        
        today_swaps = RentalSwap.objects.filter(
            rental__user=user,
            original_station=station,
            swapped_at__date=today
        ).count()
        
        available_count = PowerBank.objects.filter(
            current_station=station,
            status='AVAILABLE',
            battery_level__gte=20,
            current_slot__isnull=False
        ).count()
        
        if available_count == 0:
            raise ServiceException(
                detail="No available powerbanks at this station for swap",
                code="no_powerbanks_available"
            )
        
        if today_swaps >= available_count:
            raise ServiceException(
                detail=f"Daily swap limit ({available_count}) reached for this station",
                code="swap_limit_exceeded"
            )
    
    def _get_swap_powerbank(
        self, 
        station: 'Station', 
        exclude_powerbank_id: str = None,
        requested_sn: str = None
    ) -> tuple:
        """Get an available powerbank for swap, excluding current one"""
        from api.user.stations.models import PowerBank
        
        queryset = PowerBank.objects.select_for_update().filter(
            current_station=station,
            status='AVAILABLE',
            battery_level__gte=20,
            current_slot__isnull=False
        )
        
        if exclude_powerbank_id:
            queryset = queryset.exclude(id=exclude_powerbank_id)
        
        # If user specified a powerbank, try to get it
        if requested_sn:
            powerbank = queryset.filter(serial_number=requested_sn).first()
            if not powerbank:
                raise ServiceException(
                    detail=f"Requested powerbank {requested_sn} is not available for swap",
                    code="requested_powerbank_unavailable"
                )
            return powerbank, powerbank.current_slot
        
        # Otherwise, get highest battery powerbank
        powerbank = queryset.order_by('-battery_level').first()
        
        if not powerbank:
            raise ServiceException(
                detail="No other powerbanks available for swap",
                code="no_swap_powerbank_available"
            )
        
        return powerbank, powerbank.current_slot
    
    def _send_swap_notification(self, user, rental, old_pb, new_pb) -> None:
        """Send swap confirmation notification"""
        from api.user.notifications.services import notify
        notify(
            user,
            'rental_swapped',
            async_send=True,
            rental_code=rental.rental_code,
            old_powerbank=old_pb.serial_number if old_pb else 'N/A',
            new_powerbank=new_pb.serial_number,
            new_battery_level=new_pb.battery_level
        )
