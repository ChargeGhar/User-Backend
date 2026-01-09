"""
RentalLocationService - Location Tracking Service
============================================================

Handles GPS location tracking for active rentals.

Business Logic:
- Track powerbank location during active rentals
- Update location coordinates with accuracy
- Log location history for analytics

Author: Service Splitter (Cleaned)
Date: 2025-10-17
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from django.db import transaction

from api.common.services.base import CRUDService, ServiceException
from api.user.rentals.models import RentalLocation, Rental

if TYPE_CHECKING:
    from api.user.auth.models import User


class RentalLocationService(CRUDService):
    """Service for rental location tracking"""
    
    model = RentalLocation
    
    @transaction.atomic
    def update_location(
        self,
        rental_id: str,
        user: User,
        latitude: float,
        longitude: float,
        accuracy: float = 10.0
    ) -> RentalLocation:
        """
        Update rental location with GPS coordinates.
        
        Args:
            rental_id: UUID of the active rental
            user: User making the request
            latitude: GPS latitude (-90 to 90)
            longitude: GPS longitude (-180 to 180)
            accuracy: GPS accuracy in meters (default: 10.0)
        
        Returns:
            RentalLocation: Created location record
        
        Raises:
            ServiceException: If rental not found or not active
        """
        try:
            # Validate rental exists and belongs to user
            rental = Rental.objects.get(
                id=rental_id,
                user=user,
                status='ACTIVE'
            )
            
            # Create location record
            location = RentalLocation.objects.create(
                rental=rental,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy
            )
            
            self.log_info(
                f"Location updated for rental: {rental.rental_code} "
                f"at ({latitude}, {longitude})"
            )
            
            return location
            
        except Rental.DoesNotExist:
            raise ServiceException(
                detail="Active rental not found",
                code="rental_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to update rental location")
