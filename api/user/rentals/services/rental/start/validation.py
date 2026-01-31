"""
Rental Start - Validation Module
================================

Handles all validation for starting a rental:
- User prerequisites (profile, KYC, active rentals)
- Station availability
- POSTPAID balance requirements
- Powerbank availability
"""
from __future__ import annotations

from decimal import Decimal
from typing import Tuple, TYPE_CHECKING

from api.common.services.base import ServiceException
from api.common.permissions.base import CanRentPowerBank

if TYPE_CHECKING:
    from api.user.rentals.models import Rental
    from api.user.stations.models import Station, StationSlot, PowerBank


def validate_rental_prerequisites(user) -> None:
    """
    Validate user can start rental.
    
    Checks:
    - User meets profile/KYC requirements (via CanRentPowerBank permission)
    - User doesn't have an active rental
    
    Raises:
        ServiceException if validation fails
    """
    permission = CanRentPowerBank()
    
    class MockRequest:
        def __init__(self, user):
            self.user = user
    
    mock_request = MockRequest(user)
    
    if not permission.has_permission(mock_request, None):
        raise ServiceException(
            detail="User does not meet rental requirements",
            code="rental_prerequisites_not_met"
        )
    
    # Check for existing active rentals
    from api.user.rentals.models import Rental
    
    active_rental = Rental.objects.filter(
        user=user,
        status__in=['PENDING', 'PENDING_POPUP', 'ACTIVE', 'OVERDUE']
    ).first()
    
    if active_rental:
        if active_rental.status == 'OVERDUE':
            raise ServiceException(
                detail="You have an overdue rental. Please clear payment first.",
                code="overdue_rental_exists"
            )
        raise ServiceException(
            detail="You already have an active rental",
            code="active_rental_exists"
        )
    
    # Check for unpaid completed rentals
    unpaid_rental = Rental.objects.filter(
        user=user,
        status='COMPLETED',
        payment_status='PENDING'
    ).exists()
    
    if unpaid_rental:
        raise ServiceException(
            detail="You have unpaid rental dues. Please clear payment first.",
            code="unpaid_rental_exists"
        )


def validate_station_availability(station: 'Station') -> None:
    """
    Validate station is available for rental.
    
    Checks:
    - Station is ONLINE
    - Station is not in maintenance
    
    Raises:
        ServiceException if station not available
    """
    if station.status != 'ONLINE':
        raise ServiceException(
            detail="Station is not online",
            code="station_offline"
        )
    
    if station.is_maintenance:
        raise ServiceException(
            detail="Station is under maintenance",
            code="station_maintenance"
        )


def validate_postpaid_balance(user) -> None:
    """
    Validate user has minimum balance for POSTPAID rentals.
    
    Uses POSTPAID_MINIMUM_BALANCE from AppConfig (default: NPR 50)
    
    Raises:
        ServiceException if balance insufficient
    """
    from api.user.system.services import AppConfigService
    
    config_service = AppConfigService()
    min_balance_str = config_service.get_config_cached('POSTPAID_MINIMUM_BALANCE', '50')
    min_balance = Decimal(str(min_balance_str))
    
    wallet_balance = Decimal('0')
    if hasattr(user, 'wallet') and user.wallet:
        wallet_balance = user.wallet.balance
    
    if wallet_balance < min_balance:
        raise ServiceException(
            detail=f"POSTPAID rentals require minimum wallet balance of NPR {min_balance}. "
                   f"Your balance: NPR {wallet_balance}.",
            code="insufficient_postpaid_balance"
        )


def get_available_power_bank_and_slot(
    station: 'Station'
) -> Tuple['PowerBank', 'StationSlot']:
    """
    Get available power bank and slot from station with row-level locking.
    
    Finds powerbank that:
    - Is at the specified station
    - Has status AVAILABLE
    - Has battery level >= 20%
    - Is in a slot
    
    Returns:
        Tuple of (PowerBank, StationSlot)
    
    Raises:
        ServiceException if no powerbank available
    """
    from api.user.stations.models import PowerBank
    
    # Find powerbank with sufficient battery and row-level locking
    power_bank = PowerBank.objects.select_for_update().filter(
        current_station=station,
        status='AVAILABLE',
        battery_level__gte=20,
        current_slot__isnull=False
    ).order_by('-battery_level').first()
    
    if not power_bank:
        raise ServiceException(
            detail="No power bank available with sufficient battery",
            code="no_power_bank_available"
        )
    
    # Get the slot where this powerbank is located
    slot = power_bank.current_slot
    
    if not slot or slot.status == 'MAINTENANCE':
        raise ServiceException(
            detail="Slot is not available",
            code="slot_not_available"
        )
    
    return power_bank, slot


def validate_powerbank_for_rental(
    power_bank: 'PowerBank',
    station: 'Station',
    popup_result_sn: str
) -> 'PowerBank':
    """
    Validate and fetch the actual dispensed powerbank after popup success.
    
    Ensures the powerbank returned by the device matches expectations
    and belongs to the correct station.
    
    Args:
        power_bank: Original powerbank from DB (for fallback)
        station: The station where rental started
        popup_result_sn: Serial number returned by device popup
    
    Returns:
        The validated PowerBank object
    
    Raises:
        ServiceException if validation fails
    """
    from api.user.stations.models import PowerBank
    
    if not popup_result_sn:
        raise ServiceException(
            detail="Device popup succeeded but returned no powerbank serial",
            code="popup_sn_missing"
        )
    
    # Lock and fetch the actual dispensed powerbank by serial
    actual_power_bank = PowerBank.objects.select_for_update().filter(
        serial_number=popup_result_sn,
    ).first()
    
    if not actual_power_bank:
        raise ServiceException(
            detail=f"PowerBank with serial {popup_result_sn} not found",
            code="powerbank_not_found"
        )
    
    # Validate station relationship
    if actual_power_bank.current_station_id and actual_power_bank.current_station_id != station.id:
        raise ServiceException(
            detail="PowerBank does not belong to the requested station",
            code="powerbank_station_mismatch"
        )
    
    return actual_power_bank
