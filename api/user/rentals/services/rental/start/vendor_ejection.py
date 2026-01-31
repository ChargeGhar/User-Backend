"""
Rental Start - Vendor Ejection Module
======================================

Handles vendor free ejection logic per BR13.2:
- Every vendor (Revenue or Non-Revenue) can eject one powerbank for free per day
- Free ejection only works at their assigned station
- Logged in partner_iot_history for tracking
"""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from api.user.rentals.models import Rental
    from api.user.stations.models import Station, PowerBank
    from api.partners.common.models import Partner, PartnerIotHistory

logger = logging.getLogger(__name__)


def check_vendor_free_ejection(user, station: 'Station') -> bool:
    """
    Check if user is a vendor for this station with free ejection available.
    
    Per BR13.2:
    - Every vendor gets 1 free ejection per day
    - Must be at their assigned station
    - Works for both Revenue and Non-Revenue vendors
    
    Args:
        user: The user (potential vendor)
        station: The station where ejection is requested
    
    Returns:
        True if vendor can use free ejection today, False otherwise
    """
    # Check if user has a partner profile
    if not hasattr(user, 'partner_profile'):
        return False
    
    partner = user.partner_profile
    
    # Must be a vendor
    if partner.partner_type != 'VENDOR':
        return False
    
    # Check if vendor operates this station
    from api.partners.common.repositories import StationDistributionRepository
    
    station_vendor = StationDistributionRepository.get_station_vendor(str(station.id))
    
    if not station_vendor or str(station_vendor.id) != str(partner.id):
        # Vendor doesn't operate this station
        return False
    
    # Check daily limit - has vendor used free ejection today?
    from api.partners.common.models import PartnerIotHistory
    
    today = timezone.now().date()
    used_today = PartnerIotHistory.objects.filter(
        partner=partner,
        action_type='EJECT',
        is_free_ejection=True,
        created_at__date=today
    ).exists()
    
    return not used_today


def log_vendor_free_ejection(
    user,
    station: 'Station',
    rental: 'Rental',
    powerbank: 'PowerBank'
) -> Optional['PartnerIotHistory']:
    """
    Log free ejection to partner_iot_history after successful rental start.
    
    Only call this after confirming vendor free ejection is applicable
    via check_vendor_free_ejection().
    
    Args:
        user: The vendor user
        station: The station
        rental: The rental that triggered the ejection
        powerbank: The ejected powerbank
    
    Returns:
        PartnerIotHistory record if created, None otherwise
    """
    if not hasattr(user, 'partner_profile'):
        return None
    
    partner = user.partner_profile
    
    if partner.partner_type != 'VENDOR':
        return None
    
    try:
        from api.partners.common.models import PartnerIotHistory
        
        return PartnerIotHistory.objects.create(
            partner=partner,
            performed_by=user,
            station=station,
            action_type='EJECT',
            performed_from='MOBILE_APP',
            powerbank_sn=powerbank.serial_number,
            slot_number=rental.slot.slot_number if rental.slot else None,
            rental=rental,
            is_free_ejection=True,
            is_successful=True
        )
    except Exception as e:
        logger.error(f"Failed to log vendor free ejection: {e}")
        return None


def get_vendor_free_ejection_status(user, station: 'Station') -> dict:
    """
    Get detailed status of vendor free ejection for a station.
    
    Useful for displaying in app UI whether vendor can use free ejection.
    
    Returns:
        Dictionary with status details:
        {
            'is_vendor': bool,
            'operates_station': bool,
            'free_ejection_available': bool,
            'used_today': bool,
            'used_at': datetime or None
        }
    """
    result = {
        'is_vendor': False,
        'operates_station': False,
        'free_ejection_available': False,
        'used_today': False,
        'used_at': None
    }
    
    if not hasattr(user, 'partner_profile'):
        return result
    
    partner = user.partner_profile
    
    if partner.partner_type != 'VENDOR':
        return result
    
    result['is_vendor'] = True
    
    # Check station assignment
    from api.partners.common.repositories import StationDistributionRepository
    
    station_vendor = StationDistributionRepository.get_station_vendor(str(station.id))
    
    if station_vendor and str(station_vendor.id) == str(partner.id):
        result['operates_station'] = True
    else:
        return result
    
    # Check today's usage
    from api.partners.common.models import PartnerIotHistory
    
    today = timezone.now().date()
    today_usage = PartnerIotHistory.objects.filter(
        partner=partner,
        action_type='EJECT',
        is_free_ejection=True,
        created_at__date=today
    ).first()
    
    if today_usage:
        result['used_today'] = True
        result['used_at'] = today_usage.created_at
    else:
        result['free_ejection_available'] = True
    
    return result
