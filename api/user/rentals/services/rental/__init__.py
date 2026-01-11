"""
Rental Service
==============

Main RentalService class combining all operation mixins.
Split into sub-modules for maintainability and scalability.
"""
from api.common.services.base import CRUDService
from api.user.rentals.models import Rental

from .start import RentalStartMixin
from .cancel import RentalCancelMixin
from .extend import RentalExtendMixin
from .return_powerbank import RentalReturnMixin
from .queries import RentalQueryMixin
from .notifications import RentalNotificationMixin


class RentalService(
    RentalNotificationMixin,
    RentalStartMixin,
    RentalCancelMixin,
    RentalExtendMixin,
    RentalReturnMixin,
    RentalQueryMixin,
    CRUDService
):
    """
    Service for rental operations.
    
    Methods:
        - start_rental(user, station_sn, package_id) -> Rental
        - cancel_rental(rental_id, user, reason) -> Rental
        - extend_rental(rental_id, user, package_id) -> RentalExtension
        - return_power_bank(rental_id, return_station_sn, return_slot_number) -> Rental
        - get_user_rentals(user, filters) -> Dict
        - get_active_rental(user) -> Optional[Rental]
        - get_rental_stats(user) -> Dict
    """
    model = Rental


__all__ = [
    "RentalService",
]
