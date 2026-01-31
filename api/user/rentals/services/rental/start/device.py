"""
Rental Start - Device Module
============================

Handles device communication for rental start:
- Trigger powerbank popup
- Handle success/failure/timeout
- Schedule async verification
"""
from __future__ import annotations

import logging
from typing import Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from api.user.rentals.models import Rental
    from api.user.stations.models import Station, PowerBank

logger = logging.getLogger(__name__)


def trigger_device_popup(
    rental: 'Rental',
    station: 'Station',
    power_bank: 'PowerBank',
    specific_sn: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Trigger device popup and handle result.
    
    Flow:
    1. Call device API (popup_specific or popup_random)
    2. If success, return (True, powerbank_sn)
    3. If timeout/failure, schedule async verification and return (False, None)
    
    Args:
        rental: The rental being started
        station: Station to popup from
        power_bank: Expected powerbank (for verification)
        specific_sn: If user selected a specific powerbank
    
    Returns:
        Tuple[success, powerbank_sn]
    """
    from api.user.stations.services.device_api_service import get_device_api_service
    from api.user.stations.tasks import verify_popup_completion
    
    device_service = get_device_api_service()
    
    try:
        if specific_sn:
            # User selected specific powerbank
            success, result, message = device_service.popup_specific(
                station.serial_number, specific_sn
            )
            powerbank_sn = result.powerbank_sn if result else None
        else:
            # Random popup
            success, powerbank_sn, message = device_service.popup_random(
                station.serial_number,
                min_power=20
            )
        
        if success:
            return True, powerbank_sn
        else:
            # Popup failed - schedule async verification
            rental.rental_metadata['popup_message'] = message
            rental.save(update_fields=['rental_metadata'])
            
            verify_popup_completion.apply_async(
                args=[str(rental.id), station.serial_number, power_bank.serial_number],
                countdown=10
            )
            return False, None
            
    except Exception as e:
        # Timeout or error - schedule async verification
        logger.error(f"Device popup error for rental {rental.rental_code}: {e}")
        rental.rental_metadata['popup_error'] = str(e)
        rental.save(update_fields=['rental_metadata'])
        
        verify_popup_completion.apply_async(
            args=[str(rental.id), station.serial_number, power_bank.serial_number],
            countdown=10
        )
        return False, None


def activate_rental_powerbank(
    rental: 'Rental',
    actual_power_bank: 'PowerBank'
) -> None:
    """
    Assign powerbank to rental after successful popup.
    
    Updates powerbank status to RENTED and links to rental.
    
    Args:
        rental: The rental to update
        actual_power_bank: The dispensed powerbank
    """
    from api.user.stations.services import PowerBankService
    
    powerbank_service = PowerBankService()
    powerbank_service.assign_power_bank_to_rental(actual_power_bank, rental)
